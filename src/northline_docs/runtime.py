from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

from northline_docs.catalog import EndpointCatalog, corpus_identifiers
from northline_docs.chunking import chunk_documents
from northline_docs.corpus import load_corpus
from northline_docs.embeddings import Embedder, HashingEmbedder, OpenAIEmbedder
from northline_docs.generation.extractive import ExtractiveGenerator
from northline_docs.paths import repo_root
from northline_docs.pipeline import Generator, RagPipeline, Retriever
from northline_docs.retrieval.faiss_store import FaissRetriever
from northline_docs.retrieval.fixed import FixedRetriever
from northline_docs.types import Chunk, Document

OFFLINE_METRICS = (
    "non_llm_context_recall",
    "string_presence",
    "refusal_correctness",
    "retrieval_hit_rate",
    "mrr",
    "endpoint_validity",
    "version_correctness",
)
LIVE_METRICS = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
)


@dataclass(frozen=True)
class Settings:
    top_k: int
    overlap_threshold: float
    embedding_dim: int
    naive_doc_ids: tuple[str, ...]
    openai_model: str
    openai_embedding_model: str


@dataclass(frozen=True)
class Thresholds:
    offline: dict[str, float]
    live: dict[str, float]


@dataclass
class Runtime:
    root: Path
    documents: list[Document]
    chunks: list[Chunk]
    chunks_by_id: dict[str, Chunk]
    catalog: EndpointCatalog
    identifiers: frozenset[str]
    settings: Settings
    thresholds: Thresholds
    embedder: Embedder
    improved_retriever: FaissRetriever
    naive_retriever: FixedRetriever

    def pipeline(self, variant: str, generator: Generator | None = None) -> RagPipeline:
        retriever: Retriever
        if variant == "improved":
            retriever = self.improved_retriever
            guardrails = True
        elif variant == "naive":
            retriever = self.naive_retriever
            guardrails = False
        else:
            raise ValueError(f"Unknown variant: {variant}")
        return RagPipeline(
            retriever=retriever,
            generator=generator or ExtractiveGenerator(),
            catalog=self.catalog,
            identifiers=self.identifiers,
            top_k=self.settings.top_k,
            overlap_threshold=self.settings.overlap_threshold,
            guardrails_enabled=guardrails,
            variant=variant,
        )


def load_runtime(root: Path | None = None) -> Runtime:
    project = root or repo_root()
    documents = load_corpus(project / "corpus")
    chunks = chunk_documents(documents)
    settings = load_settings(project / "config" / "settings.yaml")
    embedder = _load_embedder(settings)
    improved = FaissRetriever(embedder)
    improved.index(chunks)
    naive = FixedRetriever(chunks, settings.naive_doc_ids)
    by_id = {chunk.doc_id: chunk for chunk in chunks}
    return Runtime(
        root=project,
        documents=documents,
        chunks=chunks,
        chunks_by_id=by_id,
        catalog=EndpointCatalog.from_documents(documents),
        identifiers=corpus_identifiers(documents),
        settings=settings,
        thresholds=load_thresholds(project / "config" / "thresholds.yaml"),
        embedder=embedder,
        improved_retriever=improved,
        naive_retriever=naive,
    )


def _load_embedder(settings: Settings) -> Embedder:
    kind = os.environ.get("NORTHLINE_EMBEDDINGS", "hashing")
    if kind == "hashing":
        return HashingEmbedder(dim=settings.embedding_dim)
    if kind == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("NORTHLINE_EMBEDDINGS=openai requires OPENAI_API_KEY")
        return OpenAIEmbedder(api_key, model=settings.openai_embedding_model)
    raise ValueError(f"Unknown NORTHLINE_EMBEDDINGS value: {kind}")


def load_settings(path: Path) -> Settings:
    raw = _load_yaml_dict(path)
    naive = raw.get("naive_doc_ids")
    if not isinstance(naive, list) or not all(isinstance(item, str) for item in naive):
        raise ValueError("settings.naive_doc_ids must be a list of strings")
    return Settings(
        top_k=_positive_int(raw, "top_k"),
        overlap_threshold=_unit_float(raw, "overlap_threshold"),
        embedding_dim=_positive_int(raw, "embedding_dim"),
        naive_doc_ids=tuple(naive),
        openai_model=_string(raw, "openai_model"),
        openai_embedding_model=_string(raw, "openai_embedding_model"),
    )


def load_thresholds(path: Path) -> Thresholds:
    raw = _load_yaml_dict(path)
    offline = _float_map(raw.get("offline"), "offline")
    live = _float_map(raw.get("live"), "live")
    missing_offline = [name for name in OFFLINE_METRICS if name not in offline]
    missing_live = [name for name in LIVE_METRICS if name not in live]
    if missing_offline or missing_live:
        raise ValueError(f"Thresholds missing metrics: {missing_offline + missing_live}")
    return Thresholds(offline=offline, live=live)


def _load_yaml_dict(path: Path) -> dict[str, object]:
    loaded: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must be a mapping")
    result: dict[str, object] = {}
    for key, value in loaded.items():
        if not isinstance(key, str):
            raise ValueError(f"{path} has a non-string key")
        result[key] = value
    return result


def _float_map(raw: object, label: str) -> dict[str, float]:
    if not isinstance(raw, dict):
        raise ValueError(f"{label} thresholds must be a mapping")
    parsed: dict[str, float] = {}
    for key, value in raw.items():
        if (
            not isinstance(key, str)
            or isinstance(value, bool)
            or not isinstance(value, int | float)
        ):
            raise ValueError(f"{label}.{key} must be a number")
        parsed[key] = float(value)
    return parsed


def _positive_int(raw: dict[str, object], key: str) -> int:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"settings.{key} must be a positive integer")
    return value


def _unit_float(raw: dict[str, object], key: str) -> float:
    value = raw.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"settings.{key} must be a number")
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"settings.{key} must be between 0 and 1")
    return number


def _string(raw: dict[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"settings.{key} must be a string")
    return value


def chunk_versions(chunks: Sequence[Chunk]) -> dict[str, str]:
    return {chunk.doc_id: chunk.version for chunk in chunks}
