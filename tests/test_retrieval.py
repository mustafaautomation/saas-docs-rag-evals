from __future__ import annotations

import numpy as np

from northline_docs.embeddings import HashingEmbedder
from northline_docs.retrieval.faiss_store import FaissRetriever
from northline_docs.retrieval.pgvector import create_extension_sql, create_table_sql, search_sql
from northline_docs.runtime import Runtime


def test_hashing_embedder_is_deterministic_and_normalized() -> None:
    embedder = HashingEmbedder(dim=64)
    first = embedder.embed(["v1 live rate limit", "v2 webhook signature"])
    second = embedder.embed(["v1 live rate limit", "v2 webhook signature"])
    assert first.shape == (2, 64)
    assert np.allclose(first, second)
    norms = np.linalg.norm(first, axis=1)
    assert np.allclose(norms, 1.0)


def test_faiss_ranks_the_labelled_rate_limit_doc_first(runtime: Runtime) -> None:
    hits = runtime.improved_retriever.search(
        "What is the v1 live rate limit?",
        k=5,
        versions={"v1", "shared"},
    )
    assert hits[0].chunk.doc_id == "v1-rate-limits"
    assert all(hit.chunk.version != "v2" for hit in hits)


def test_fixed_retriever_ignores_the_query(runtime: Runtime) -> None:
    hits = runtime.naive_retriever.search("What is the v2 live rate limit?", k=4, versions={"v2"})
    assert [hit.chunk.doc_id for hit in hits] == list(runtime.settings.naive_doc_ids)


def test_pgvector_sql_uses_cosine_distance() -> None:
    assert "vector" in create_extension_sql()
    table = create_table_sql("northline_chunks", 384)
    assert "vector(384)" in table
    filtered = search_sql("northline_chunks", filter_versions=True)
    assert "<=>" in filtered
    assert "version = ANY(%s)" in filtered
    assert "<=>" in search_sql("northline_chunks", filter_versions=False)


def test_retriever_index_round_trip(runtime: Runtime) -> None:
    embedder = HashingEmbedder(dim=runtime.settings.embedding_dim)
    store = FaissRetriever(embedder)
    store.index(runtime.chunks)
    hits = store.search("POST /v2/customers account_ref tax_id", k=3, versions={"v2", "shared"})
    assert hits[0].chunk.doc_id == "v2-customers"
