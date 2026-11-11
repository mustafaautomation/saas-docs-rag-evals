from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from northline_docs.embeddings import Embedder
from northline_docs.textutil import content_overlap
from northline_docs.types import Chunk, ScoredChunk

_TABLE = re.compile(r"[a-z_][a-z0-9_]*")
DEFAULT_DSN = "postgresql://northline:northline@localhost:5432/northline"


def create_extension_sql() -> str:
    return "CREATE EXTENSION IF NOT EXISTS vector"


def create_table_sql(table: str, dim: int) -> str:
    _check_table(table)
    if dim < 1:
        raise ValueError("dim must be positive")
    return (
        f"CREATE TABLE {table} ("
        "chunk_id text PRIMARY KEY, "
        "doc_id text NOT NULL, "
        "title text NOT NULL, "
        "version text NOT NULL, "
        "content text NOT NULL, "
        f"embedding vector({dim}))"
    )


def search_sql(table: str, *, filter_versions: bool) -> str:
    _check_table(table)
    where = "WHERE version = ANY(%s)" if filter_versions else ""
    return (
        "SELECT chunk_id, doc_id, title, version, content, "
        f"(embedding <=> %s) AS distance FROM {table} {where} "
        "ORDER BY embedding <=> %s LIMIT %s"
    )


class PgVectorRetriever:
    """Postgres + pgvector retriever. Optional. Tests and CI use FAISS instead."""

    def __init__(self, dsn: str, embedder: Embedder, *, table: str = "northline_chunks") -> None:
        _check_table(table)
        self._dsn = dsn
        self._embedder = embedder
        self._table = table
        self._chunks: dict[str, Chunk] = {}

    def index(self, chunks: Sequence[Chunk]) -> None:
        import psycopg
        from pgvector.psycopg import register_vector

        self._chunks = {chunk.chunk_id: chunk for chunk in chunks}
        vectors = self._embedder.embed([chunk.text for chunk in chunks])
        try:
            with psycopg.connect(self._dsn) as conn:
                register_vector(conn)
                conn.execute(create_extension_sql())
                conn.execute(f"DROP TABLE IF EXISTS {self._table}")
                conn.execute(create_table_sql(self._table, self._embedder.dim))
                rows = [
                    (
                        chunk.chunk_id,
                        chunk.doc_id,
                        chunk.title,
                        chunk.version,
                        chunk.text,
                        vectors[index],
                    )
                    for index, chunk in enumerate(chunks)
                ]
                with conn.cursor() as cursor:
                    cursor.executemany(
                        f"INSERT INTO {self._table} "
                        "(chunk_id, doc_id, title, version, content, embedding) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        rows,
                    )
                conn.execute(
                    f"CREATE INDEX ON {self._table} USING hnsw (embedding vector_cosine_ops)"
                )
        except psycopg.Error as exc:
            raise RuntimeError(
                "Could not index chunks in Postgres. Start the compose file and set "
                "NORTHLINE_DATABASE_URL."
            ) from exc

    def search(self, query: str, k: int, versions: set[str] | None) -> list[ScoredChunk]:
        import psycopg
        from pgvector.psycopg import register_vector

        if k < 1:
            raise ValueError("k must be at least 1")
        vector = self._embedder.embed([query])[0]
        sql = search_sql(self._table, filter_versions=versions is not None)
        # Fetch the filtered rows and re-rank with the same hybrid score as FAISS.
        fetch = max(k, 1000)
        params: tuple[Any, ...]
        if versions is None:
            params = (vector, vector, fetch)
        else:
            params = (vector, list(versions), vector, fetch)
        try:
            with psycopg.connect(self._dsn) as conn:
                register_vector(conn)
                rows = conn.execute(sql, params).fetchall()
        except psycopg.Error as exc:
            raise RuntimeError("Postgres search failed. Check NORTHLINE_DATABASE_URL.") from exc
        hits: list[ScoredChunk] = []
        for row in rows:
            chunk = self._chunks.get(str(row[0]))
            text = str(row[4])
            if chunk is None:
                chunk = Chunk(
                    chunk_id=str(row[0]),
                    doc_id=str(row[1]),
                    title=str(row[2]),
                    version=str(row[3]),
                    text=text,
                    index=0,
                )
            distance = float(row[5])
            hits.append(
                ScoredChunk(
                    chunk=chunk,
                    score=(1.0 - distance) + content_overlap(query, chunk.text),
                )
            )
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:k]


def _check_table(table: str) -> None:
    if _TABLE.fullmatch(table) is None:
        raise ValueError(f"Unsafe SQL table name: {table}")
