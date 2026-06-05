from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.models import Document, DocumentChunk, DocumentSection
from app.domains.documents.parser import read_text_from_path, split_child_chunks, split_parent_sections


SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".text", ".pdf"}


def safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._")
    return cleaned or "document.txt"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_document_from_upload(
    db: Session,
    file_obj: BinaryIO,
    filename: str,
    doc_type: str,
    title: str | None = None,
) -> Document:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported extension {extension}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")

    upload_dir = get_settings().upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4()}-{safe_filename(filename)}"
    file_path = upload_dir / stored_name
    with file_path.open("wb") as target:
        shutil.copyfileobj(file_obj, target)

    document = Document(
        title=title or Path(filename).stem or filename,
        doc_type=doc_type,
        source_type="upload",
        file_path=str(file_path),
        content_hash=sha256_file(file_path),
        parse_status="uploaded",
        index_status="not_indexed",
        metadata_={
            "original_filename": filename,
            "extension": extension,
            "stored_filename": stored_name,
        },
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def create_document_from_text(db: Session, title: str, doc_type: str, content: str) -> Document:
    upload_dir = get_settings().upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4()}-{safe_filename(title)}.txt"
    file_path = upload_dir / stored_name
    file_path.write_text(content, encoding="utf-8")

    document = Document(
        title=title,
        doc_type=doc_type,
        source_type="manual_text",
        file_path=str(file_path),
        content_hash=sha256_text(content),
        parse_status="uploaded",
        index_status="not_indexed",
        metadata_={
            "original_filename": f"{title}.txt",
            "extension": ".txt",
            "stored_filename": stored_name,
        },
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def parse_document(db: Session, document_id: str) -> dict:
    document = db.get(Document, document_id)
    if document is None:
        raise ValueError(f"Document not found: {document_id}")
    if not document.file_path:
        raise ValueError("Document has no file path to parse.")

    document.parse_status = "parsing"
    document.index_status = "not_indexed"
    db.commit()

    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
    db.query(DocumentSection).filter(DocumentSection.document_id == document.id).delete()
    db.flush()

    text = read_text_from_path(Path(document.file_path))
    sections = split_parent_sections(text)
    chunk_count = 0

    for section_data in sections:
        section = DocumentSection(
            document_id=document.id,
            user_id=document.user_id,
            title=section_data.title,
            section_path=section_data.section_path,
            content=section_data.content,
            start_offset=section_data.start_offset,
            end_offset=section_data.end_offset,
            token_count=estimate_token_count(section_data.content),
            order_index=section_data.order_index,
        )
        db.add(section)
        db.flush()

        for chunk_data in split_child_chunks(section_data.content):
            chunk = DocumentChunk(
                document_id=document.id,
                section_id=section.id,
                user_id=document.user_id,
                content=chunk_data.content,
                content_hash=sha256_text(chunk_data.content),
                chunk_index=chunk_count,
                start_offset=section_data.start_offset + chunk_data.start_offset,
                end_offset=section_data.start_offset + chunk_data.end_offset,
                token_count=estimate_token_count(chunk_data.content),
                embedding_status="pending",
                bm25_status="pending",
                graph_status="pending",
                metadata_={"section_chunk_index": chunk_data.chunk_index},
            )
            db.add(chunk)
            chunk_count += 1

    document.parse_status = "parsed"
    document.index_status = "ready_for_indexing" if chunk_count else "empty"
    document.metadata_ = {
        **(document.metadata_ or {}),
        "section_count": len(sections),
        "chunk_count": chunk_count,
    }
    db.commit()
    db.refresh(document)
    return {
        "document_id": document.id,
        "section_count": len(sections),
        "chunk_count": chunk_count,
        "parse_status": document.parse_status,
        "index_status": document.index_status,
    }


def mark_document_failed(db: Session, document_id: str, message: str) -> None:
    document = db.get(Document, document_id)
    if document is None:
        return
    document.parse_status = "failed"
    document.metadata_ = {**(document.metadata_ or {}), "parse_error": message}
    db.commit()


def delete_document(db: Session, document_id: str) -> dict | None:
    document = db.get(Document, document_id)
    if document is None:
        return None

    file_deleted = delete_stored_file(document.file_path)
    db.delete(document)
    db.commit()
    return {
        "document_id": document_id,
        "file_deleted": file_deleted,
    }


def delete_stored_file(file_path: str | None) -> bool:
    if not file_path:
        return False

    path = Path(file_path)
    upload_dir = get_settings().upload_dir.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(upload_dir)
    except ValueError:
        return False

    if not resolved_path.is_file():
        return False

    resolved_path.unlink()
    return True


def list_documents(db: Session, limit: int = 30, doc_type: str | None = None) -> list[Document]:
    statement = select(Document).options(selectinload(Document.sections), selectinload(Document.chunks))
    if doc_type:
        statement = statement.where(Document.doc_type == doc_type)
    statement = statement.order_by(desc(Document.created_at)).limit(limit)
    return list(db.scalars(statement))


def get_document(db: Session, document_id: str) -> Document | None:
    statement = (
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.sections), selectinload(Document.chunks))
    )
    return db.scalar(statement)


def count_documents(db: Session) -> dict[str, int]:
    return {
        "documents": db.scalar(select(func.count(Document.id))) or 0,
        "sections": db.scalar(select(func.count(DocumentSection.id))) or 0,
        "chunks": db.scalar(select(func.count(DocumentChunk.id))) or 0,
    }


def estimate_token_count(text: str) -> int:
    if not text:
        return 0
    # A cheap approximation; exact tokenizer support comes later with embeddings.
    return max(1, len(text) // 4)
