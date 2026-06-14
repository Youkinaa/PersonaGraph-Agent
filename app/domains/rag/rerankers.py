from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings, get_settings


class RerankProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class RerankResult:
    index: int
    score: float


def rerank_evidence_pack(
    query: str,
    evidence: list[dict],
    top_k: int,
    settings: Settings | None = None,
) -> tuple[list[dict], dict]:
    settings = settings or get_settings()
    metadata = {
        "enabled": settings.rag_rerank_enabled,
        "model": settings.rerank_model_id,
        "candidate_count": len(evidence),
        "returned": min(top_k, len(evidence)),
        "status": "skipped",
    }
    if not settings.rag_rerank_enabled:
        return mark_rrf_rank(evidence[:top_k]), metadata
    if len(evidence) <= 1:
        return mark_rrf_rank(evidence[:top_k]), metadata

    documents = [format_evidence_document(item, settings.rag_rerank_document_max_chars) for item in evidence]
    results = OpenAICompatibleRerankClient(settings).rerank(query=query, documents=documents, top_n=top_k)
    ranked = apply_rerank_results(evidence, results, top_k=top_k, model_id=settings.rerank_model_id)
    metadata.update(
        {
            "returned": len(ranked),
            "status": "succeeded",
        }
    )
    return ranked, metadata


def mark_rrf_rank(evidence: list[dict]) -> list[dict]:
    ranked: list[dict] = []
    for rank, item in enumerate(evidence):
        updated = dict(item)
        updated["rank_source"] = "rrf"
        updated["final_rank"] = rank
        ranked.append(updated)
    return ranked


def apply_rerank_results(
    evidence: list[dict],
    results: list[RerankResult],
    top_k: int,
    model_id: str,
) -> list[dict]:
    ranked: list[dict] = []
    used_indexes: set[int] = set()
    for rank, result in enumerate(results):
        if result.index < 0 or result.index >= len(evidence) or result.index in used_indexes:
            continue
        used_indexes.add(result.index)
        updated = dict(evidence[result.index])
        updated["rank_source"] = "rerank"
        updated["final_rank"] = rank
        updated["rerank"] = {
            "model": model_id,
            "score": round(result.score, 6),
            "original_index": result.index,
        }
        ranked.append(updated)
        if len(ranked) >= top_k:
            return ranked

    for original_index, item in enumerate(evidence):
        if original_index in used_indexes:
            continue
        updated = dict(item)
        updated["rank_source"] = "rrf_fallback"
        updated["final_rank"] = len(ranked)
        ranked.append(updated)
        if len(ranked) >= top_k:
            break
    return ranked


def format_evidence_document(evidence: dict, max_chars: int) -> str:
    document = evidence.get("document", {})
    parent = evidence.get("parent", {})
    chunk = evidence.get("chunk", {})
    parts = [
        f"Title: {document.get('title') or ''}",
        f"Document type: {document.get('doc_type') or ''}",
        f"Section: {parent.get('title') or parent.get('section_path') or ''}",
        f"Chunk: {chunk.get('content') or ''}",
    ]
    parent_content = parent.get("content")
    if parent_content and parent_content != chunk.get("content"):
        parts.append(f"Parent context: {parent_content}")
    text = "\n".join(part for part in parts if part.strip())
    return text[: max(200, max_chars)]


def resolve_rerank_endpoints(base_url: str) -> list[str]:
    raw = base_url.rstrip("/")
    if raw.endswith("/reranks"):
        return [raw]

    normalized = raw.replace("/compatible-mode/", "/compatible-api/")
    endpoints = [f"{normalized}/reranks"]
    fallback = f"{raw}/reranks"
    if fallback not in endpoints:
        endpoints.append(fallback)
    return endpoints


class OpenAICompatibleRerankClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.api_key = settings.effective_rerank_api_key
        self.base_url = settings.effective_rerank_base_url
        self.model_id = settings.rerank_model_id
        self.instruct = settings.rerank_instruct

    def rerank(self, query: str, documents: list[str], top_n: int) -> list[RerankResult]:
        if not documents:
            return []
        if self.api_key is None:
            raise RerankProviderError("Rerank API key is not configured.")
        if not self.base_url:
            raise RerankProviderError("Rerank base URL is not configured.")

        last_error: str | None = None
        for endpoint in resolve_rerank_endpoints(self.base_url):
            for include_instruct in [True, False] if self.instruct else [False]:
                try:
                    return self._request(endpoint, query, documents, top_n, include_instruct=include_instruct)
                except RerankProviderError as exc:
                    last_error = str(exc)
                    if "status 404" not in last_error and "status 405" not in last_error and include_instruct is False:
                        raise
        raise RerankProviderError(last_error or "Rerank request failed.")

    def _request(
        self,
        endpoint: str,
        query: str,
        documents: list[str],
        top_n: int,
        include_instruct: bool,
    ) -> list[RerankResult]:
        payload: dict[str, Any] = {
            "model": self.model_id,
            "query": query,
            "documents": documents,
            "top_n": min(top_n, len(documents)),
        }
        if include_instruct and self.instruct:
            payload["instruct"] = self.instruct
        headers = {
            "authorization": f"Bearer {self.api_key.get_secret_value()}",
            "content-type": "application/json",
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(endpoint, json=payload, headers=headers)
        if response.status_code >= 400:
            raise RerankProviderError(f"Rerank request failed with status {response.status_code}.")
        return parse_rerank_response(response.json())


def parse_rerank_response(payload: dict) -> list[RerankResult]:
    raw_results = payload.get("results")
    if raw_results is None:
        raw_results = payload.get("output", {}).get("results")
    if not isinstance(raw_results, list):
        raise RerankProviderError("Rerank response shape is invalid.")

    results: list[RerankResult] = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        index = item.get("index")
        score = item.get("relevance_score", item.get("score"))
        if index is None or score is None:
            continue
        results.append(RerankResult(index=int(index), score=float(score)))
    if not results and raw_results:
        raise RerankProviderError("Rerank response does not contain valid scores.")
    return results
