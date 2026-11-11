from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    version: str
    body: str
    text: str
    source_path: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    version: str
    text: str
    index: int


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: float


@dataclass(frozen=True)
class Answer:
    question: str
    response: str
    retrieved: tuple[ScoredChunk, ...]
    version: str | None
    behavior: str
    variant: str
