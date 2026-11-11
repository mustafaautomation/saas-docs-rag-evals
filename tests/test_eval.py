from __future__ import annotations

import json
from pathlib import Path

import pytest

from northline_docs.eval.dataset import Question
from northline_docs.eval.gate import apply_gate
from northline_docs.eval.metrics import score_records
from northline_docs.eval.ragas_live import (
    LiveEvalUnavailable,
    ragas_metric_names,
    require_openai_key,
)
from northline_docs.eval.records import read_jsonl, run_questions
from northline_docs.eval.report import render_markdown, write_png
from northline_docs.guardrails import NAIVE_LEAK
from northline_docs.runtime import OFFLINE_METRICS, Runtime, chunk_versions


def test_ragas_metric_names_match_the_pinned_api() -> None:
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )

    assert ragas_metric_names() == (
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
    )
    assert all(
        metric is not None
        for metric in (Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall)
    )


def test_improved_passes_gate_and_naive_fails(runtime: Runtime, questions: list[Question]) -> None:
    versions = chunk_versions(runtime.chunks)
    improved_records = run_questions(runtime.pipeline("improved"), questions, runtime.chunks_by_id)
    naive_records = run_questions(runtime.pipeline("naive"), questions, runtime.chunks_by_id)
    improved_scores, improved_rows = score_records(
        improved_records,
        catalog_unknown=runtime.catalog.unknown_endpoints,
        chunk_versions=versions,
    )
    naive_scores, _naive_rows = score_records(
        naive_records,
        catalog_unknown=runtime.catalog.unknown_endpoints,
        chunk_versions=versions,
    )
    improved_gate = apply_gate(improved_scores, runtime.thresholds.offline)
    naive_gate = apply_gate(naive_scores, runtime.thresholds.offline)
    assert improved_gate.passed, improved_gate.failures
    assert not naive_gate.passed
    assert set(improved_scores) == set(OFFLINE_METRICS)
    assert all(score == 1.0 for score in improved_scores.values())
    assert naive_scores["version_correctness"] < runtime.thresholds.offline["version_correctness"]
    assert naive_scores["refusal_correctness"] < 1.0
    assert naive_scores["endpoint_validity"] < 1.0
    assert all(not row.failure_names() for row in improved_rows)
    assert any(NAIVE_LEAK in record.response for record in naive_records)
    assert all(NAIVE_LEAK not in record.response for record in improved_records)


def test_snapshot_matches_a_fresh_run(runtime: Runtime, questions: list[Question]) -> None:
    recorded = {
        record.id: record
        for record in read_jsonl(runtime.root / "evals" / "snapshots" / "improved.jsonl")
    }
    fresh = run_questions(runtime.pipeline("improved"), questions, runtime.chunks_by_id)
    assert {record.id for record in fresh} == set(recorded)
    for record in fresh:
        saved = recorded[record.id]
        assert record.response == saved.response
        assert record.retrieved_doc_ids == saved.retrieved_doc_ids
        assert record.retrieved_contexts == saved.retrieved_contexts


def test_judge_file_is_labelled_and_has_no_scores(root: Path) -> None:
    path = root / "evals" / "snapshots" / "judge_scores.example.jsonl"
    rows = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert len(rows) == 1
    assert rows[0]["label"] == "illustrative_example_not_a_measurement"
    assert rows[0]["scores"] is None


def test_report_contains_the_comparison_and_not_the_leak(
    runtime: Runtime, questions: list[Question], tmp_path: Path
) -> None:
    versions = chunk_versions(runtime.chunks)
    improved_records = run_questions(runtime.pipeline("improved"), questions, runtime.chunks_by_id)
    naive_records = run_questions(runtime.pipeline("naive"), questions, runtime.chunks_by_id)
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
    markdown = render_markdown(
        improved_scores=improved_scores,
        naive_scores=naive_scores,
        thresholds=runtime.thresholds.offline,
        improved_rows=improved_rows,
        naive_rows=naive_rows,
        question_count=len(questions),
        doc_count=len(runtime.documents),
    )
    assert "improved" in markdown
    assert "naive" in markdown
    assert "| string_presence | 1.0000 |" in markdown
    assert NAIVE_LEAK not in markdown
    assert "Not run" in markdown
    png = tmp_path / "eval-report.png"
    write_png(
        png,
        improved_scores=improved_scores,
        naive_scores=naive_scores,
        thresholds=runtime.thresholds.offline,
    )
    assert png.read_bytes().startswith(b"\x89PNG")


def test_live_mode_requires_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LiveEvalUnavailable):
        require_openai_key()
