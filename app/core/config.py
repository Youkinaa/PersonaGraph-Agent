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
    debug: bool = Field(default=True, validation_alias="APP_DEBUG")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    document_upload_dir: str = Field(default="uploads/documents", validation_alias="DOCUMENT_UPLOAD_DIR")

    llm_api_key: SecretStr | None = Field(default=None, validation_alias="LLM_API_KEY")
    llm_model_id: str | None = Field(default=None, validation_alias="LLM_MODEL_ID")
    llm_base_url: str | None = Field(default=None, validation_alias="LLM_BASE_URL")
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

    def public_summary(self) -> dict[str, Any]:
        """Return non-secret settings suitable for status pages and health checks."""

        return {
            "app_name": self.app_name,
            "app_env": self.app_env,
            "app_version": self.app_version,
            "debug": self.debug,
            "document_upload_dir": str(self.upload_dir),
            "llm_model_id": self.llm_model_id,
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
