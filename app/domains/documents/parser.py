from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParsedSection:
    title: str | None
    section_path: str | None
    content: str
    start_offset: int
    end_offset: int
    order_index: int


@dataclass(frozen=True)
class ParsedChunk:
    content: str
    start_offset: int
    end_offset: int
    chunk_index: int


HEADING_PATTERN = re.compile(
    r"^\s*(#{1,6}\s+.+|[一二三四五六七八九十]+[、.．]\s*.+|\d+([.．、]\d+)*[.．、]\s*.+|[A-Z][A-Z0-9 /_-]{3,})\s*$"
)


def read_text_from_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return read_pdf_text(path)
    if suffix in {".txt", ".md", ".markdown", ".text"}:
        return read_plain_text(path)
    raise ValueError(f"Unsupported document type: {suffix or 'unknown'}")


def read_plain_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def read_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - dependency availability
        raise RuntimeError("PDF parsing requires pypdf to be installed.") from exc

    reader = PdfReader(str(path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"\n\n[Page {index}]\n{text}")
    return "\n".join(pages)


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def split_parent_sections(text: str, target_size: int = 2200) -> list[ParsedSection]:
    text = normalize_text(text)
    if not text:
        return []

    heading_matches = []
    offset = 0
    for line in text.splitlines(keepends=True):
        line_text = line.strip()
        if HEADING_PATTERN.match(line_text):
            heading_matches.append((offset, line_text))
        offset += len(line)

    if heading_matches:
        return split_by_headings(text, heading_matches)
    return split_by_size(text, target_size=target_size)


def split_by_headings(text: str, headings: list[tuple[int, str]]) -> list[ParsedSection]:
    sections: list[ParsedSection] = []
    if headings[0][0] > 0 and text[: headings[0][0]].strip():
        sections.append(
            ParsedSection(
                title="Introduction",
                section_path="Introduction",
                content=text[: headings[0][0]].strip(),
                start_offset=0,
                end_offset=headings[0][0],
                order_index=0,
            )
        )

    for index, (start, title) in enumerate(headings):
        end = headings[index + 1][0] if index + 1 < len(headings) else len(text)
        content = text[start:end].strip()
        if not content:
            continue
        sections.append(
            ParsedSection(
                title=clean_heading(title),
                section_path=clean_heading(title),
                content=content,
                start_offset=start,
                end_offset=end,
                order_index=len(sections),
            )
        )
    return sections


def split_by_size(text: str, target_size: int = 2200) -> list[ParsedSection]:
    paragraphs = re.split(r"\n\s*\n", text)
    sections: list[ParsedSection] = []
    buffer: list[str] = []
    buffer_start = 0
    cursor = 0

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            cursor += 2
            continue
        if not buffer:
            buffer_start = text.find(paragraph, cursor)
        buffer.append(paragraph)
        current = "\n\n".join(buffer)
        if len(current) >= target_size:
            end = buffer_start + len(current)
            sections.append(
                ParsedSection(
                    title=f"Section {len(sections) + 1}",
                    section_path=f"Section {len(sections) + 1}",
                    content=current,
                    start_offset=max(buffer_start, 0),
                    end_offset=end,
                    order_index=len(sections),
                )
            )
            buffer = []
        cursor += len(paragraph) + 2

    if buffer:
        current = "\n\n".join(buffer)
        sections.append(
            ParsedSection(
                title=f"Section {len(sections) + 1}",
                section_path=f"Section {len(sections) + 1}",
                content=current,
                start_offset=max(buffer_start, 0),
                end_offset=max(buffer_start, 0) + len(current),
                order_index=len(sections),
            )
        )
    return sections


def split_child_chunks(text: str, chunk_size: int = 900, overlap: int = 120) -> list[ParsedChunk]:
    text = normalize_text(text)
    if not text:
        return []
    if len(text) <= chunk_size:
        return [ParsedChunk(content=text, start_offset=0, end_offset=len(text), chunk_index=0)]

    chunks: list[ParsedChunk] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = max(text.rfind("\n\n", start, end), text.rfind("。", start, end), text.rfind(".", start, end))
            if boundary > start + int(chunk_size * 0.55):
                end = boundary + 1
        content = text[start:end].strip()
        if content:
            chunks.append(
                ParsedChunk(
                    content=content,
                    start_offset=start,
                    end_offset=end,
                    chunk_index=len(chunks),
                )
            )
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def clean_heading(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^#{1,6}\s+", "", value)
    return value.strip()
