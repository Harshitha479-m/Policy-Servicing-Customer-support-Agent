from __future__ import annotations

import hashlib
import pickle
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from app.ingestion import DocumentChunk, serialize_chunks


@dataclass(frozen=True)
class SearchResult:
    chunk: DocumentChunk
    score: float


class LocalVectorStore:
    """Small persisted local vector database using deterministic local embeddings."""

    def __init__(self, matrix: Any, chunks: list[DocumentChunk], dimensions: int = 384):
        self.matrix = matrix
        self.chunks = chunks
        self.dimensions = dimensions

    @staticmethod
    def _embed(text: str, dimensions: int = 384) -> np.ndarray:
        vector = np.zeros(dimensions, dtype=np.float32)
        tokens = text.lower().split()
        for token in tokens:
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % dimensions
            vector[index] += 1.0
        norm = np.linalg.norm(vector)
        return vector / norm if norm else vector

    @classmethod
    def build(cls, chunks: list[DocumentChunk]) -> "LocalVectorStore":
        if not chunks:
            raise ValueError("Cannot build a vector store with no document chunks")
        matrix = np.vstack([cls._embed(chunk.text) for chunk in chunks])
        return cls(matrix, chunks)

    def search(self, query: str, top_k: int = 5, min_score: float = 0.08) -> list[SearchResult]:
        if not query.strip():
            return []
        query_vector = self._embed(query, self.dimensions)
        scores = self.matrix @ query_vector
        stop_words = {"the", "and", "what", "does", "this", "that", "with", "from", "for", "are", "is", "how", "can", "you"}
        query_terms = {term for term in re.findall(r"[a-z0-9]+", query.lower()) if len(term) > 2 and term not in stop_words}
        indices = np.argsort(scores)[::-1]
        results = []
        for index in indices:
            chunk_terms = {term for term in re.findall(r"[a-z0-9]+", self.chunks[index].text.lower()) if term not in stop_words}
            if scores[index] < min_score or not query_terms.intersection(chunk_terms):
                continue
            results.append(SearchResult(self.chunks[index], float(scores[index])))
            if len(results) == top_k:
                break
        return results

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            pickle.dump({"matrix": self.matrix, "chunks": serialize_chunks(self.chunks), "dimensions": self.dimensions}, handle)

    @classmethod
    def load(cls, path: Path) -> "LocalVectorStore":
        with path.open("rb") as handle:
            payload = pickle.load(handle)
        chunks = [DocumentChunk(**item) for item in payload["chunks"]]
        return cls(payload["matrix"], chunks, payload.get("dimensions", 384))
