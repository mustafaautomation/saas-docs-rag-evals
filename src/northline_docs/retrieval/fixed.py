from __future__ import annotations

from collections.abc import Sequence

from northline_docs.types import Chunk, ScoredChunk


class FixedRetriever:
    """Broken retriever. It ignores the query and the version and returns a fixed doc list.

    This is the before-state in the eval report. It exists so the gate has a regression to catch.
    """

    def __init__(self, chunks: Sequence[Chunk], doc_ids: Sequence[str]) -> None:
        by_id = {chunk.doc_id: chunk for chunk in chunks}
        missing = [doc_id for doc_id in doc_ids if doc_id not in by_id]
        if missing:
            raise ValueError(f"Fixed retriever doc ids are not in the corpus: {missing}")
        self._chunks = [by_id[doc_id] for doc_id in doc_ids]

    def search(self, query: str, k: int, versions: set[str] | None) -> list[ScoredChunk]:
        del query, versions
        if k < 1:
            raise ValueError("k must be at least 1")
        return [
            ScoredChunk(chunk=chunk, score=1.0 - (index * 0.01))
            for index, chunk in enumerate(self._chunks[:k])
        ]
