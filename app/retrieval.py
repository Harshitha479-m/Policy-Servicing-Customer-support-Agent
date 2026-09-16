from __future__ import annotations

from dataclasses import dataclass

from app.vector_store import LocalVectorStore, SearchResult


@dataclass(frozen=True)
class RetrievedContext:
    results: list[SearchResult]

    @property
    def has_evidence(self) -> bool:
        return bool(self.results)

    def as_prompt_context(self) -> str:
        return "\n\n".join(
            f"[{index}] {result.chunk.text} (source={result.chunk.source}, page={result.chunk.page or 'n/a'})"
            for index, result in enumerate(self.results, start=1)
        )


def retrieve(query: str, store: LocalVectorStore, top_k: int, min_score: float) -> RetrievedContext:
    return RetrievedContext(store.search(query, top_k=top_k, min_score=min_score))
