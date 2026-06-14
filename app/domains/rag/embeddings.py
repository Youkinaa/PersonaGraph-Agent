from __future__ import annotations

import hashlib
import logging
import math
import re
from collections.abc import Iterable

import httpx

from app.core.config import Settings, get_settings


logger = logging.getLogger(__name__)
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_+#.-]+|[\u4e00-\u9fff]{2,}")


class EmbeddingProviderError(RuntimeError):
    pass


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text or "")]


def hash_embed_text(text: str, dimension: int = 128) -> list[float]:
    """Return a deterministic local embedding for tests and fallback."""

    vector = [0.0] * dimension
    tokens = tokenize(text)
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = 1.0 + min(len(token), 12) / 12
        vector[index] += sign * weight

    return normalize_vector(vector)


def embed_text(text: str, dimension: int = 128) -> list[float]:
    """Backward-compatible alias for the local hashing embedding."""

    return hash_embed_text(text, dimension)


def embed_query(query: str, settings: Settings | None = None) -> list[float]:
    return embed_texts([query], settings=settings)[0]


def embed_texts(texts: list[str], settings: Settings | None = None) -> list[list[float]]:
    settings = settings or get_settings()
    if settings.rag_embedding_provider == "hash":
        return [hash_embed_text(text, settings.rag_embedding_dim) for text in texts]

    try:
        return OpenAICompatibleEmbeddingClient(settings).embed_texts(texts)
    except Exception as exc:
        if not settings.rag_embedding_fallback_to_hash:
            raise
        logger.warning(
            "Embedding provider failed; falling back to local hash embeddings. provider=%s model=%s "
            "dimension=%s text_count=%s error=%s",
            settings.rag_embedding_provider,
            settings.embedding_model_id,
            settings.rag_embedding_dim,
            len(texts),
            exc,
        )
        return [hash_embed_text(text, settings.rag_embedding_dim) for text in texts]


class OpenAICompatibleEmbeddingClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.api_key = settings.effective_embedding_api_key
        self.base_url = settings.effective_embedding_base_url
        self.model_id = settings.embedding_model_id
        self.dimension = settings.rag_embedding_dim
        self.batch_size = max(1, min(settings.embedding_batch_size, 10))

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.api_key is None:
            raise EmbeddingProviderError("Embedding API key is not configured.")
        if not self.base_url:
            raise EmbeddingProviderError("Embedding base URL is not configured.")

        vectors: list[list[float]] = []
        for batch in batched(texts, self.batch_size):
            vectors.extend(self._embed_batch(batch))
        return vectors

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        endpoint = f"{self.base_url.rstrip('/')}/embeddings"
        payload = {
            "model": self.model_id,
            "input": texts,
            "dimensions": self.dimension,
            "encoding_format": "float",
        }
        headers = {
            "authorization": f"Bearer {self.api_key.get_secret_value()}",
            "content-type": "application/json",
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(endpoint, json=payload, headers=headers)
        if response.status_code >= 400:
            raise EmbeddingProviderError(f"Embedding request failed with status {response.status_code}.")

        data = response.json().get("data", [])
        ordered = sorted(data, key=lambda item: item.get("index", 0))
        vectors = [item.get("embedding") for item in ordered]
        if len(vectors) != len(texts) or any(not isinstance(vector, list) for vector in vectors):
            raise EmbeddingProviderError("Embedding response shape is invalid.")
        return [normalize_vector([float(value) for value in vector]) for vector in vectors]


def batched(items: list[str], batch_size: int) -> Iterable[list[str]]:
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def normalize_vector(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]
