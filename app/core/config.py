from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = Field(default="PersonaGraph Career Agent", validation_alias="APP_NAME")
    app_env: str = Field(default="local", validation_alias="APP_ENV")
    app_version: str = Field(default="0.1.0", validation_alias="APP_VERSION")
    app_phase: str = Field(default="phase_4_hybrid_rag", validation_alias="APP_PHASE")
    app_phase_label: str = Field(default="Phase 4", validation_alias="APP_PHASE_LABEL")
    debug: bool = Field(default=True, validation_alias="APP_DEBUG")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    document_upload_dir: str = Field(default="uploads/documents", validation_alias="DOCUMENT_UPLOAD_DIR")
    document_parser_provider: str = Field(default="simple_text", validation_alias="DOCUMENT_PARSER_PROVIDER")
    document_parse_strategy_version: str = Field(
        default="simple_text_parent_child_v1",
        validation_alias="DOCUMENT_PARSE_STRATEGY_VERSION",
    )
    document_text_extraction_mode: str = Field(default="text_only", validation_alias="DOCUMENT_TEXT_EXTRACTION_MODE")
    document_parent_target_chars: int = Field(default=2200, validation_alias="DOCUMENT_PARENT_TARGET_CHARS")
    document_child_chunk_size: int = Field(default=900, validation_alias="DOCUMENT_CHILD_CHUNK_SIZE")
    document_child_chunk_overlap: int = Field(default=120, validation_alias="DOCUMENT_CHILD_CHUNK_OVERLAP")
    document_ocr_enabled: bool = Field(default=False, validation_alias="DOCUMENT_OCR_ENABLED")
    document_ocr_provider: str = Field(default="reserved", validation_alias="DOCUMENT_OCR_PROVIDER")
    document_multimodal_enabled: bool = Field(default=False, validation_alias="DOCUMENT_MULTIMODAL_ENABLED")
    document_image_extensions: list[str] = Field(
        default=[".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"],
        validation_alias="DOCUMENT_IMAGE_EXTENSIONS",
    )
    rag_es_index: str = Field(default="persona_graph_chunks", validation_alias="RAG_ES_INDEX")
    rag_milvus_collection: str = Field(
        default="persona_graph_chunks_v4",
        validation_alias="RAG_MILVUS_COLLECTION",
    )
    rag_embedding_dim: int = Field(default=1024, validation_alias="RAG_EMBEDDING_DIM")
    rag_embedding_provider: str = Field(default="openai_compatible", validation_alias="RAG_EMBEDDING_PROVIDER")
    rag_embedding_fallback_to_hash: bool = Field(
        default=True,
        validation_alias="RAG_EMBEDDING_FALLBACK_TO_HASH",
    )
    rag_rerank_enabled: bool = Field(default=True, validation_alias="RAG_RERANK_ENABLED")
    rag_rerank_candidate_multiplier: int = Field(default=4, validation_alias="RAG_RERANK_CANDIDATE_MULTIPLIER")
    rag_rerank_document_max_chars: int = Field(default=2400, validation_alias="RAG_RERANK_DOCUMENT_MAX_CHARS")

    llm_api_key: SecretStr | None = Field(default=None, validation_alias="LLM_API_KEY")
    llm_model_id: str | None = Field(default=None, validation_alias="LLM_MODEL_ID")
    llm_base_url: str | None = Field(default=None, validation_alias="LLM_BASE_URL")
    embedding_api_key: SecretStr | None = Field(default=None, validation_alias="EMBEDDING_API_KEY")
    embedding_model_id: str = Field(default="text-embedding-v4", validation_alias="EMBEDDING_MODEL_ID")
    embedding_base_url: str | None = Field(default=None, validation_alias="EMBEDDING_BASE_URL")
    embedding_batch_size: int = Field(default=10, validation_alias="EMBEDDING_BATCH_SIZE")
    rerank_api_key: SecretStr | None = Field(default=None, validation_alias="RERANK_API_KEY")
    rerank_model_id: str = Field(default="qwen3-rerank", validation_alias="RERANK_MODEL_ID")
    rerank_base_url: str | None = Field(default=None, validation_alias="RERANK_BASE_URL")
    rerank_instruct: str | None = Field(
        default="Rank the documents by how useful they are as evidence for a career assistant.",
        validation_alias="RERANK_INSTRUCT",
    )
    serpapi_api_key: SecretStr | None = Field(default=None, validation_alias="SERPAPI_API_KEY")

    database_url: SecretStr = Field(
        default=SecretStr("postgresql+psycopg://app:change_me_123@127.0.0.1:5432/app_db"),
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://127.0.0.1:6379/0", validation_alias="REDIS_URL")
    milvus_uri: str = Field(default="http://127.0.0.1:19530", validation_alias="MILVUS_URI")
    elasticsearch_url: str = Field(default="http://127.0.0.1:9200", validation_alias="ELASTICSEARCH_URL")
    neo4j_uri: str = Field(default="bolt://127.0.0.1:7687", validation_alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", validation_alias="NEO4J_USER")
    neo4j_password: SecretStr | None = Field(default=None, validation_alias="NEO4J_PASSWORD")

    @property
    def base_dir(self) -> Path:
        return BASE_DIR

    @property
    def templates_dir(self) -> Path:
        return BASE_DIR / "app" / "templates"

    @property
    def static_dir(self) -> Path:
        return BASE_DIR / "app" / "static"

    @property
    def upload_dir(self) -> Path:
        upload_path = Path(self.document_upload_dir)
        if upload_path.is_absolute():
            return upload_path
        return BASE_DIR / upload_path

    @property
    def effective_embedding_base_url(self) -> str | None:
        return self.embedding_base_url or self.llm_base_url

    @property
    def effective_embedding_api_key(self) -> SecretStr | None:
        return self.embedding_api_key or self.llm_api_key

    @property
    def effective_rerank_base_url(self) -> str | None:
        return self.rerank_base_url or self.llm_base_url

    @property
    def effective_rerank_api_key(self) -> SecretStr | None:
        return self.rerank_api_key or self.llm_api_key

    def public_summary(self) -> dict[str, Any]:
        """Return non-secret settings suitable for status pages and health checks."""

        return {
            "app_name": self.app_name,
            "app_env": self.app_env,
            "app_version": self.app_version,
            "app_phase": self.app_phase,
            "app_phase_label": self.app_phase_label,
            "debug": self.debug,
            "document_upload_dir": str(self.upload_dir),
            "document_parser_provider": self.document_parser_provider,
            "document_parse_strategy_version": self.document_parse_strategy_version,
            "document_text_extraction_mode": self.document_text_extraction_mode,
            "document_parent_target_chars": self.document_parent_target_chars,
            "document_child_chunk_size": self.document_child_chunk_size,
            "document_child_chunk_overlap": self.document_child_chunk_overlap,
            "document_ocr_enabled": self.document_ocr_enabled,
            "document_ocr_provider": self.document_ocr_provider,
            "document_multimodal_enabled": self.document_multimodal_enabled,
            "document_image_extensions": self.document_image_extensions,
            "rag_es_index": self.rag_es_index,
            "rag_milvus_collection": self.rag_milvus_collection,
            "rag_embedding_dim": self.rag_embedding_dim,
            "rag_embedding_provider": self.rag_embedding_provider,
            "rag_rerank_enabled": self.rag_rerank_enabled,
            "rag_rerank_candidate_multiplier": self.rag_rerank_candidate_multiplier,
            "rag_rerank_document_max_chars": self.rag_rerank_document_max_chars,
            "llm_model_id": self.llm_model_id,
            "embedding_model_id": self.embedding_model_id,
            "embedding_base_url_configured": self.effective_embedding_base_url is not None,
            "has_embedding_api_key": self.effective_embedding_api_key is not None,
            "rerank_model_id": self.rerank_model_id,
            "rerank_base_url_configured": self.effective_rerank_base_url is not None,
            "has_rerank_api_key": self.effective_rerank_api_key is not None,
            "has_llm_api_key": self.llm_api_key is not None,
            "has_serpapi_api_key": self.serpapi_api_key is not None,
            "database_url_configured": self.database_url is not None,
            "redis_url": self.redis_url,
            "milvus_uri": self.milvus_uri,
            "elasticsearch_url": self.elasticsearch_url,
            "neo4j_uri": self.neo4j_uri,
            "neo4j_user": self.neo4j_user,
            "neo4j_password_configured": self.neo4j_password is not None,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
