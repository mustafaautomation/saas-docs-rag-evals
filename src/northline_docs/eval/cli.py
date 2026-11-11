from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from northline_docs.eval.dataset import load_questions
from northline_docs.eval.gate import GateResult, apply_gate
from northline_docs.eval.metrics import score_records
from northline_docs.eval.ragas_live import (
    LiveEvalUnavailable,
    require_openai_key,
    score_with_ragas_sync,
)
from northline_docs.eval.records import (
    SnapshotStale,
    assert_snapshot_current,
    read_jsonl,
    run_questions,
    write_jsonl,
)
from northline_docs.eval.report import write_reports
from northline_docs.generation.openai import OpenAIChatClient, OpenAIGenerator
from northline_docs.runtime import chunk_versions, load_runtime


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="northline-eval")
    parser.add_argument("--mode", choices=("offline", "live"), default="offline")
    parser.add_argument("--variant", choices=("improved", "naive"), default="improved")
    parser.add_argument("--refresh-snapshot", action="store_true")
    parser.add_argument("--write-report", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        return _run(args.mode, args.variant, args.refresh_snapshot, args.write_report, args.root)
    except (LiveEvalUnavailable, SnapshotStale, FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


def _run(
    mode: str,
    variant: str,
    refresh_snapshot: bool,
    write_report: bool,
    root: Path | None,
) -> int:
    runtime = load_runtime(root)
    questions_path = runtime.root / "evals" / "questions.jsonl"
    questions = load_questions(questions_path, known_doc_ids=set(runtime.chunks_by_id))
    snapshot_dir = runtime.root / "evals" / "snapshots"
    improved_path = snapshot_dir / "improved.jsonl"
    naive_path = snapshot_dir / "naive.jsonl"

    if refresh_snapshot:
        improved_records = run_questions(
            runtime.pipeline("improved"), questions, runtime.chunks_by_id
        )
        naive_records = run_questions(runtime.pipeline("naive"), questions, runtime.chunks_by_id)
        write_jsonl(improved_path, improved_records)
        write_jsonl(naive_path, naive_records)
        print(f"Wrote {improved_path}")
        print(f"Wrote {naive_path}")
    if not improved_path.is_file() or not naive_path.is_file():
        raise FileNotFoundError(
            "Missing eval snapshots. Run `uv run northline-eval --refresh-snapshot`."
        )

    improved_records = read_jsonl(improved_path)
    naive_records = read_jsonl(naive_path)
    assert_snapshot_current(improved_records, runtime.chunks_by_id)
    assert_snapshot_current(naive_records, runtime.chunks_by_id)
    versions = chunk_versions(runtime.chunks)

    if mode == "live":
        api_key = require_openai_key()
        client = OpenAIChatClient(api_key, model=runtime.settings.openai_model)
        live_pipeline = runtime.pipeline("improved", generator=OpenAIGenerator(client))
        judged_records = run_questions(live_pipeline, questions, runtime.chunks_by_id)
        live_scores = score_with_ragas_sync(
            judged_records,
            api_key=api_key,
            chat_model=runtime.settings.openai_model,
            embedding_model=runtime.settings.openai_embedding_model,
        )
        judge_path = snapshot_dir / "judge_scores.jsonl"
        _write_live_scores(judge_path, live_scores)
        print(f"Wrote {judge_path}")
        for name, score in live_scores.items():
            print(f"live {name} {score:.4f}")
        live_gate = apply_gate(live_scores, runtime.thresholds.live)
        _print_gate("live", live_gate)
        offline_scores, _rows = score_records(
            judged_records,
            catalog_unknown=runtime.catalog.unknown_endpoints,
            chunk_versions=versions,
        )
        offline_gate = apply_gate(offline_scores, runtime.thresholds.offline)
        _print_gate("live-pipeline-offline-metrics", offline_gate)
        return 0 if live_gate.passed and offline_gate.passed else 1

    improved_scores, improved_rows = score_records(
        improved_records,
        catalog_unknown=runtime.catalog.unknown_endpoints,
        chunk_versions=versions,
    )
    naive_scores, naive_rows = score_records(
        naive_records,
        catalog_unknown=runtime.catalog.unknown_endpoints,
        chunk_versions=versions,
    )
    selected_scores = improved_scores if variant == "improved" else naive_scores
    gate = apply_gate(selected_scores, runtime.thresholds.offline)
    _print_scores(variant, selected_scores)
    _print_gate(variant, gate)
    if write_report and variant == "improved":
        report_dir = runtime.root / "docs"
        md_path, html_path, png_path = write_reports(
            report_dir,
            improved_scores=improved_scores,
            naive_scores=naive_scores,
            thresholds=runtime.thresholds.offline,
            improved_rows=improved_rows,
            naive_rows=naive_rows,
            question_count=len(questions),
            doc_count=len(runtime.documents),
        )
        print(f"Wrote {md_path}")
        print(f"Wrote {html_path}")
        print(f"Wrote {png_path}")
    return 0 if gate.passed else 1


def _print_scores(variant: str, scores: dict[str, float]) -> None:
    for name in sorted(scores):
        print(f"{variant} {name} {scores[name]:.4f}")


def _print_gate(variant: str, gate: GateResult) -> None:
    if gate.passed:
        print(f"{variant} gate: pass")
        return
    print(f"{variant} gate: fail")
    for failure in gate.failures:
        print(f"  {failure}")


def _write_live_scores(path: Path, scores: dict[str, float]) -> None:
    payload = {
        "label": "live_run",
        "note": "Scores from a real RAGAS live run. Measured, not illustrative.",
        "scores": scores,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
