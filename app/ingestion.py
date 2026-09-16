from __future__ import annotations

import hashlib
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    text: str
    source: str
    page: int | None
    document_type: str
    metadata: dict[str, Any]


def extract_document(path: Path) -> list[tuple[str, int | None]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("Install pypdf to ingest PDF files") from exc
        return [(page.extract_text() or "", index + 1) for index, page in enumerate(PdfReader(str(path)).pages)]
    if suffix == ".docx":
        try:
            from docx import Document
        except ImportError as exc:
            raise RuntimeError("Install python-docx to ingest DOCX files") from exc
        return [("\n".join(paragraph.text for paragraph in Document(str(path)).paragraphs), None)]
    if suffix in {".txt", ".md"}:
        return [(path.read_text(encoding="utf-8"), None)]
    raise ValueError(f"Unsupported document type: {path.suffix}")


def chunk_text(text: str, chunk_size: int = 850, overlap: int = 120) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + chunk_size)
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = end - overlap
    return chunks


def ingest_file(path: Path, chunk_size: int = 850, overlap: int = 120) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for page_text, page_number in extract_document(path):
        for index, text in enumerate(chunk_text(page_text, chunk_size, overlap)):
            raw_id = f"{path.name}:{page_number or 0}:{index}:{text}"
            chunk_id = hashlib.sha256(raw_id.encode()).hexdigest()[:16]
            chunks.append(DocumentChunk(
                chunk_id=chunk_id,
                text=text,
                source=path.name,
                page=page_number,
                document_type=path.suffix.lower().lstrip("."),
                metadata={"source": path.name, "page": page_number, "document_type": path.suffix.lower().lstrip(".")},
            ))
    return chunks


def ingest_directory(directory: Path) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.suffix.lower() in {".pdf", ".docx", ".txt", ".md"}:
            logger.info("Ingesting %s", path)
            chunks.extend(ingest_file(path))
    return chunks


def serialize_chunks(chunks: list[DocumentChunk]) -> list[dict[str, Any]]:
    return [asdict(chunk) for chunk in chunks]
