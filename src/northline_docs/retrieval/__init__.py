"""Retrievers. FAISS is the default. pgvector is optional.

The fixed retriever is the broken baseline used to prove the eval gate.
"""

from northline_docs.retrieval.faiss_store import FaissRetriever
from northline_docs.retrieval.fixed import FixedRetriever
from northline_docs.retrieval.pgvector import PgVectorRetriever

__all__ = ["FaissRetriever", "FixedRetriever", "PgVectorRetriever"]
