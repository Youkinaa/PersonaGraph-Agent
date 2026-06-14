import logging
from types import SimpleNamespace

from app.domains.rag import embeddings as embedding_module
from app.domains.rag.embeddings import hash_embed_text
from app.domains.rag.fusion import reciprocal_rank_fusion
from app.domains.rag.rerankers import (
    RerankResult,
    apply_rerank_results,
    parse_rerank_response,
    resolve_rerank_endpoints,
)
from app.domains.rag.schemas import RetrievalHit
from app.domains.rag.versioning import document_version_status, strategy_version
from app.db.models import Document


def test_hash_embedding_is_deterministic() -> None:
    first = hash_embed_text("LangGraph FastAPI PostgreSQL", dimension=16)
    second = hash_embed_text("LangGraph FastAPI PostgreSQL", dimension=16)

    assert first == second
    assert len(first) == 16
    assert any(value != 0 for value in first)


def test_embedding_fallback_logs_warning(monkeypatch, caplog) -> None:
    class FailingEmbeddingClient:
        def __init__(self, settings) -> None:
            self.settings = settings

        def embed_texts(self, texts: list[str]) -> list[list[float]]:
            raise RuntimeError("provider unavailable")

    settings = SimpleNamespace(
        rag_embedding_provider="openai_compatible",
        rag_embedding_fallback_to_hash=True,
        rag_embedding_dim=8,
        embedding_model_id="text-embedding-v4",
    )
    monkeypatch.setattr(embedding_module, "OpenAICompatibleEmbeddingClient", FailingEmbeddingClient)

    with caplog.at_level(logging.WARNING, logger=embedding_module.__name__):
        vectors = embedding_module.embed_texts(["LangGraph RAG"], settings=settings)

    assert len(vectors) == 1
    assert len(vectors[0]) == 8
    assert "falling back to local hash embeddings" in caplog.text


def test_reciprocal_rank_fusion_merges_sources() -> None:
    fused = reciprocal_rank_fusion(
        [
            [RetrievalHit(chunk_id="a", score=2.0, source="bm25", rank=0)],
            [RetrievalHit(chunk_id="a", score=0.9, source="vector", rank=0)],
        ]
    )

    assert len(fused) == 1
    assert fused[0].chunk_id == "a"
    assert fused[0].sources == ["bm25", "vector"]
    assert fused[0].source_scores == {"bm25": 2.0, "vector": 0.9}


def test_dashscope_rerank_endpoint_prefers_compatible_api() -> None:
    endpoints = resolve_rerank_endpoints("https://dashscope.aliyuncs.com/compatible-mode/v1")

    assert endpoints[0] == "https://dashscope.aliyuncs.com/compatible-api/v1/reranks"
    assert endpoints[1] == "https://dashscope.aliyuncs.com/compatible-mode/v1/reranks"


def test_parse_rerank_response_supports_top_level_results() -> None:
    results = parse_rerank_response(
        {
            "results": [
                {"index": 1, "relevance_score": 0.91},
                {"index": 0, "relevance_score": 0.42},
            ]
        }
    )

    assert results == [RerankResult(index=1, score=0.91), RerankResult(index=0, score=0.42)]


def test_apply_rerank_results_reorders_evidence() -> None:
    evidence = [
        {"chunk_id": "a", "rrf_score": 0.01},
        {"chunk_id": "b", "rrf_score": 0.02},
    ]

    ranked = apply_rerank_results(
        evidence,
        [RerankResult(index=1, score=0.98), RerankResult(index=0, score=0.2)],
        top_k=2,
        model_id="qwen3-rerank",
    )

    assert [item["chunk_id"] for item in ranked] == ["b", "a"]
    assert ranked[0]["rank_source"] == "rerank"
    assert ranked[0]["rerank"]["model"] == "qwen3-rerank"


def test_strategy_version_is_stable_and_changes_with_payload() -> None:
    first = strategy_version("index", {"schema": "index_strategy_v1", "embedding": {"model": "a"}})
    second = strategy_version("index", {"embedding": {"model": "a"}, "schema": "index_strategy_v1"})
    changed = strategy_version("index", {"schema": "index_strategy_v1", "embedding": {"model": "b"}})

    assert first == second
    assert first != changed
    assert first.startswith("index_strategy_v1:index:")


def test_legacy_parsed_document_requires_reparse() -> None:
    document = Document(
        id="doc-1",
        title="Legacy Resume",
        doc_type="resume",
        parse_status="parsed",
        index_status="indexed",
        metadata_={},
    )

    status = document_version_status(document)

    assert status.parse_stale is True
    assert status.recommended_action == "reparse"
