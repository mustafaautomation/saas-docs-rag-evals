from __future__ import annotations

import argparse
import os
import sys

from northline_docs.generation.extractive import ExtractiveGenerator
from northline_docs.pipeline import RagPipeline
from northline_docs.retrieval.pgvector import DEFAULT_DSN, PgVectorRetriever
from northline_docs.runtime import load_runtime
from northline_docs.textutil import content_overlap, detect_version


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="northline-ask")
    parser.add_argument("question")
    parser.add_argument("--variant", choices=("improved", "naive"), default="improved")
    parser.add_argument("--retriever", choices=("memory", "pgvector"), default=None)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)

    runtime = load_runtime()
    retriever_name = args.retriever or os.environ.get("NORTHLINE_RETRIEVER", "memory")
    if retriever_name not in {"memory", "pgvector"}:
        print(f"Unknown retriever {retriever_name}", file=sys.stderr)
        return 2

    pipeline: RagPipeline
    if retriever_name == "pgvector" and args.variant == "improved":
        store = PgVectorRetriever(
            os.environ.get("NORTHLINE_DATABASE_URL", DEFAULT_DSN),
            runtime.embedder,
        )
        store.index(runtime.chunks)
        pipeline = RagPipeline(
            retriever=store,
            generator=ExtractiveGenerator(),
            catalog=runtime.catalog,
            identifiers=runtime.identifiers,
            top_k=runtime.settings.top_k,
            overlap_threshold=runtime.settings.overlap_threshold,
            guardrails_enabled=True,
            variant="improved",
        )
    else:
        pipeline = runtime.pipeline(args.variant)

    result = pipeline.answer(args.question)
    print(result.response)
    if args.debug:
        print("\n--- debug ---")
        print(f"variant: {result.variant}")
        print(f"behavior: {result.behavior}")
        print(f"version: {detect_version(args.question)}")
        for hit in result.retrieved:
            overlap = content_overlap(args.question, hit.chunk.text)
            print(
                f"{hit.chunk.doc_id}\t{hit.chunk.version}\t"
                f"score={hit.score:.4f}\toverlap={overlap:.4f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
