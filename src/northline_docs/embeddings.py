from __future__ import annotations

import hashlib
import itertools
from collections.abc import Sequence
from typing import Any, Protocol

import numpy as np

from northline_docs.textutil import content_token_list

FloatMatrix = np.ndarray[Any, np.dtype[np.float32]]


class Embedder(Protocol):
    dim: int

    def embed(self, texts: Sequence[str]) -> FloatMatrix: ...


class HashingEmbedder:
    """Deterministic feature-hashing embedder. No network and no model download."""

    def __init__(
        self,
        dim: int = 384,
        *,
        use_bigrams: bool = True,
        max_tokens: int | None = None,
    ) -> None:
        if dim < 8:
            raise ValueError("dim must be at least 8")
        self.dim = dim
        self._use_bigrams = use_bigrams
        self._max_tokens = max_tokens

    def embed(self, texts: Sequence[str]) -> FloatMatrix:
        matrix = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            tokens = content_token_list(text)
            if self._max_tokens is not None:
                tokens = tokens[: self._max_tokens]
            for token in tokens:
                index, sign = _bucket(f"uni:{token}", self.dim)
                matrix[row, index] += sign * 2.0
            if self._use_bigrams:
                for left, right in itertools.pairwise(tokens):
                    index, sign = _bucket(f"bi:{left}:{right}", self.dim)
                    matrix[row, index] += sign
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms = np.maximum(norms, np.float32(1e-12))
        matrix /= norms
        return matrix


class OpenAIEmbedder:
    """OpenAI embeddings. Used only when a caller opts in. Offline eval does not."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        from openai import OpenAI

        self.dim = 1536
        self._model = model
        self._client = OpenAI(api_key=api_key)

    def embed(self, texts: Sequence[str]) -> FloatMatrix:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        response = self._client.embeddings.create(model=self._model, input=list(texts))
        ordered = sorted(response.data, key=lambda item: item.index)
        matrix = np.asarray([item.embedding for item in ordered], dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms = np.maximum(norms, np.float32(1e-12))
        matrix /= norms
        return matrix


def _bucket(token: str, dim: int) -> tuple[int, float]:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    index = int.from_bytes(digest[:4], "little") % dim
    sign = 1.0 if digest[4] % 2 == 0 else -1.0
    return index, sign
