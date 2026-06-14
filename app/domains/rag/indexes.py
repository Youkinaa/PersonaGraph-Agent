from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import Settings
from app.domains.rag.embeddings import embed_query
from app.domains.rag.schemas import ChunkRecord, RetrievalHit


class ElasticsearchChunkIndex:
    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.elasticsearch_url.rstrip("/")
        self.index_name = settings.rag_es_index

    def ensure_index(self) -> None:
        with httpx.Client(timeout=5.0) as client:
            response = client.head(f"{self.base_url}/{self.index_name}")
            if response.status_code == 200:
                return
            if response.status_code not in {404, 400}:
                response.raise_for_status()

            mapping = {
                "mappings": {
                    "properties": {
                        "chunk_id": {"type": "keyword"},
                        "document_id": {"type": "keyword"},
                        "section_id": {"type": "keyword"},
                        "title": {"type": "text"},
                        "doc_type": {"type": "keyword"},
                        "section_path": {"type": "text"},
                        "content": {"type": "text"},
                        "chunk_index": {"type": "integer"},
                    }
                }
            }
            create_response = client.put(f"{self.base_url}/{self.index_name}", json=mapping)
            if create_response.status_code not in {200, 201, 400}:
                create_response.raise_for_status()

    def health(self) -> dict:
        try:
            with httpx.Client(timeout=5.0) as client:
                cluster_response = client.get(self.base_url)
                cluster_response.raise_for_status()
                index_response = client.head(f"{self.base_url}/{self.index_name}")
            return {
                "status": "ok",
                "index": self.index_name,
                "index_exists": index_response.status_code == 200,
            }
        except Exception as exc:
            return {
                "status": "unavailable",
                "index": self.index_name,
                "error": str(exc),
            }

    def index_chunks(self, records: list[ChunkRecord]) -> int:
        if not records:
            return 0
        self.ensure_index()
        lines: list[str] = []
        for record in records:
            lines.append(json.dumps({"index": {"_index": self.index_name, "_id": record.chunk_id}}))
            lines.append(
                json.dumps(
                    {
                        "chunk_id": record.chunk_id,
                        "document_id": record.document_id,
                        "section_id": record.section_id,
                        "title": record.title,
                        "doc_type": record.doc_type,
                        "section_path": record.section_path,
                        "content": record.content,
                        "chunk_index": record.chunk_index,
                    },
                    ensure_ascii=False,
                )
            )

        body = "\n".join(lines) + "\n"
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"{self.base_url}/_bulk",
                content=body.encode("utf-8"),
                headers={"content-type": "application/x-ndjson"},
            )
            response.raise_for_status()
            payload = response.json()
        if payload.get("errors"):
            first_error = next((item for item in payload.get("items", []) if item.get("index", {}).get("error")), None)
            raise RuntimeError(f"Elasticsearch bulk index failed: {first_error}")
        return len(records)

    def delete_document(self, document_id: str) -> dict:
        payload = {"query": {"term": {"document_id": document_id}}}
        with httpx.Client(timeout=10.0) as client:
            response = client.post(f"{self.base_url}/{self.index_name}/_delete_by_query", json=payload)
            if response.status_code == 404:
                return {"deleted": 0, "index_exists": False}
            response.raise_for_status()
            data = response.json()
        return {"deleted": int(data.get("deleted") or 0), "index_exists": True}

    def search(self, query: str, top_k: int = 8, doc_type: str | None = None) -> list[RetrievalHit]:
        must: list[dict[str, Any]] = [
            {
                "multi_match": {
                    "query": query,
                    "fields": ["content^3", "title^2", "section_path"],
                }
            }
        ]
        filters: list[dict[str, Any]] = []
        if doc_type:
            filters.append({"term": {"doc_type": doc_type}})
        payload = {
            "size": top_k,
            "query": {
                "bool": {
                    "must": must,
                    "filter": filters,
                }
            },
        }
        with httpx.Client(timeout=5.0) as client:
            response = client.post(f"{self.base_url}/{self.index_name}/_search", json=payload)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            data = response.json()

        hits = data.get("hits", {}).get("hits", [])
        return [
            RetrievalHit(
                chunk_id=item["_source"]["chunk_id"],
                score=float(item.get("_score") or 0.0),
                source="bm25",
                rank=index,
            )
            for index, item in enumerate(hits)
            if item.get("_source", {}).get("chunk_id")
        ]


class MilvusChunkIndex:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.uri = settings.milvus_uri
        self.collection_name = settings.rag_milvus_collection
        self.dimension = settings.rag_embedding_dim

    def _client(self):
        try:
            from pymilvus import MilvusClient
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("pymilvus is not installed. Run pip install -r requirements.txt.") from exc
        return MilvusClient(uri=self.uri)

    def ensure_collection(self):
        client = self._client()
        if not client.has_collection(self.collection_name):
            client.create_collection(
                collection_name=self.collection_name,
                dimension=self.dimension,
                primary_field_name="chunk_id",
                id_type="string",
                vector_field_name="embedding",
                metric_type="COSINE",
                auto_id=False,
                enable_dynamic_field=True,
                max_length=80,
            )
        else:
            self._validate_collection_dimension(client)
        return client

    def health(self) -> dict:
        try:
            client = self._client()
            exists = client.has_collection(self.collection_name)
            if exists:
                self._validate_collection_dimension(client)
            return {
                "status": "ok",
                "collection": self.collection_name,
                "collection_exists": exists,
                "dimension": self.dimension,
            }
        except Exception as exc:
            return {
                "status": "unavailable",
                "collection": self.collection_name,
                "dimension": self.dimension,
                "error": str(exc),
            }

    def _validate_collection_dimension(self, client) -> None:
        description = client.describe_collection(self.collection_name)
        fields = description.get("fields", []) if isinstance(description, dict) else []
        embedding_field = next((field for field in fields if field.get("name") == "embedding"), None)
        params = embedding_field.get("params", {}) if embedding_field else {}
        existing_dim = params.get("dim") or params.get("dimension")
        if existing_dim is not None and int(existing_dim) != self.dimension:
            raise RuntimeError(
                "Milvus collection dimension mismatch: "
                f"{self.collection_name} has dim={existing_dim}, configured dim={self.dimension}. "
                "Use a new RAG_MILVUS_COLLECTION or recreate the existing collection."
            )

    def index_chunks(self, records: list[ChunkRecord]) -> int:
        if not records:
            return 0
        client = self.ensure_collection()
        data = [
            {
                "chunk_id": record.chunk_id,
                "document_id": record.document_id,
                "section_id": record.section_id,
                "doc_type": record.doc_type,
                "content": record.content[:4096],
                "embedding": record.embedding,
            }
            for record in records
        ]
        client.upsert(collection_name=self.collection_name, data=data)
        return len(records)

    def delete_document(self, document_id: str) -> dict:
        client = self._client()
        if not client.has_collection(self.collection_name):
            return {"deleted": 0, "collection_exists": False}
        escaped_document_id = document_id.replace("\\", "\\\\").replace('"', '\\"')
        result = client.delete(
            collection_name=self.collection_name,
            filter=f'document_id == "{escaped_document_id}"',
        )
        delete_count = 0
        if isinstance(result, dict):
            delete_count = int(result.get("delete_count") or result.get("delete_cnt") or 0)
        return {"deleted": delete_count, "collection_exists": True}

    def search(self, query: str, top_k: int = 8) -> list[RetrievalHit]:
        client = self.ensure_collection()
        results = client.search(
            collection_name=self.collection_name,
            data=[embed_query(query, self.settings)],
            limit=top_k,
            output_fields=["chunk_id", "document_id", "section_id", "doc_type"],
        )
        hits = results[0] if results else []
        output: list[RetrievalHit] = []
        for index, item in enumerate(hits):
            entity = item.get("entity", {}) if isinstance(item, dict) else {}
            chunk_id = entity.get("chunk_id") or item.get("id")
            if chunk_id:
                output.append(
                    RetrievalHit(
                        chunk_id=str(chunk_id),
                        score=float(item.get("distance") or item.get("score") or 0.0),
                        source="vector",
                        rank=index,
                    )
                )
        return output
