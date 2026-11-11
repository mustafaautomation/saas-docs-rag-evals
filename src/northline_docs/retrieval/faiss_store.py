from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from northline_docs.embeddings import Embedder
from northline_docs.textutil import content_overlap
from northline_docs.types import Chunk, ScoredChunk


class FaissRetriever:
    """Exact inner-product search over L2-normalized vectors (cosine similarity)."""

    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder
        self._chunks: list[Chunk] = []
        self._index: Any = None

    def index(self, chunks: Sequence[Chunk]) -> None:
        import faiss

        faiss.omp_set_num_threads(1)
        self._chunks = list(chunks)
        if not self._chunks:
            raise ValueError("Cannot index an empty chunk list")
        vectors = np.ascontiguousarray(self._embedder.embed([chunk.text for chunk in self._chunks]))
        index = faiss.IndexFlatIP(self._embedder.dim)
        index.add(vectors)
        self._index = index

    def search(self, query: str, k: int, versions: set[str] | None) -> list[ScoredChunk]:
        if self._index is None:
            raise RuntimeError("Call index() before search()")
        if k < 1:
            raise ValueError("k must be at least 1")
        query_vector = np.ascontiguousarray(self._embedder.embed([query]))
        scores, indices = self._index.search(query_vector, len(self._chunks))
        hits: list[ScoredChunk] = []
        for score, index in zip(scores[0], indices[0], strict=True):
            if int(index) < 0:
                continue
            chunk = self._chunks[int(index)]
            if versions is not None and chunk.version not in versions:
                continue
            # Cosine plus the fraction of question terms present in the chunk.
            # API docs questions use identifiers, and the lexical term keeps those chunks on top.
            combined = float(score) + content_overlap(query, chunk.text)
            hits.append(ScoredChunk(chunk=chunk, score=combined))
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:k]
