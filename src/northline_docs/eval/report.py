from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from northline_docs.eval.metrics import QuestionScore
from northline_docs.runtime import LIVE_METRICS, OFFLINE_METRICS

DEFINITIONS = {
    "faithfulness": "Whether the answer sticks to the retrieved documentation.",
    "answer_relevancy": "Whether the answer addresses the question that was asked.",
    "context_precision": "Whether higher-ranked chunks are the ones the reference needs.",
    "context_recall": "Whether the retrieved chunks cover the claims in the reference answer.",
    "non_llm_context_recall": (
        "Whether the labelled source chunk was retrieved, using string similarity and no model."
    ),
    "string_presence": "Whether the answer contains the labelled facts from the docs.",
    "refusal_correctness": (
        "Whether secret requests, unknown endpoints, unknown parameters, "
        "and out-of-scope questions were handled as labelled."
    ),
    "retrieval_hit_rate": "Whether the labelled document appeared in the top results.",
    "mrr": "How high the labelled document ranked. 1.0 means it was first.",
    "endpoint_validity": "Whether every endpoint the answer mentions exists in the docs.",
    "version_correctness": "Whether the answer stayed on the version the user asked about.",
}


def write_reports(
    directory: Path,
    *,
    improved_scores: Mapping[str, float],
    naive_scores: Mapping[str, float],
    thresholds: Mapping[str, float],
    improved_rows: Sequence[QuestionScore],
    naive_rows: Sequence[QuestionScore],
    question_count: int,
    doc_count: int,
) -> tuple[Path, Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    markdown = render_markdown(
        improved_scores=improved_scores,
        naive_scores=naive_scores,
        thresholds=thresholds,
        improved_rows=improved_rows,
        naive_rows=naive_rows,
        question_count=question_count,
        doc_count=doc_count,
    )
    html = render_html(
        improved_scores=improved_scores,
        naive_scores=naive_scores,
        thresholds=thresholds,
        improved_rows=improved_rows,
        naive_rows=naive_rows,
        question_count=question_count,
        doc_count=doc_count,
    )
    md_path = directory / "eval-report.md"
    html_path = directory / "eval-report.html"
    png_path = directory / "eval-report.png"
    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    write_png(
        png_path,
        improved_scores=improved_scores,
        naive_scores=naive_scores,
        thresholds=thresholds,
    )
    return md_path, html_path, png_path


def render_markdown(
    *,
    improved_scores: Mapping[str, float],
    naive_scores: Mapping[str, float],
    thresholds: Mapping[str, float],
    improved_rows: Sequence[QuestionScore],
    naive_rows: Sequence[QuestionScore],
    question_count: int,
    doc_count: int,
) -> str:
    improved_failures = [row for row in improved_rows if row.failure_names()]
    naive_failures = [row for row in naive_rows if row.failure_names()]
    lines = [
        "# Northline docs eval report",
        "",
        "Offline scores from the deterministic pipeline. The corpus is synthetic.",
        "RAGAS faithfulness, answer relevancy, context precision, and context recall",
        "are not in this table: they run only in live mode, and this run had no judge scores.",
        "",
        f"Documents: {doc_count}. Questions: {question_count}.",
        "",
        "The improved column is the version-filtered retriever with guardrails.",
        "The naive column is the broken retriever and the prompt with no guardrails.",
        "The gate applies to the improved column.",
        "",
        "| metric | improved | naive | delta | threshold | gate |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for name in OFFLINE_METRICS:
        improved = improved_scores[name]
        naive = naive_scores[name]
        threshold = thresholds[name]
        gate = "pass" if improved >= threshold else "fail"
        lines.append(
            f"| {name} | {improved:.4f} | {naive:.4f} | {improved - naive:+.4f} | "
            f"{threshold:.4f} | {gate} |"
        )
    lines.extend(["", "## What the metrics mean", ""])
    for name in OFFLINE_METRICS:
        lines.append(f"- **{name}**: {DEFINITIONS[name]}")
    lines.extend(
        [
            "",
            "## Improved per-question failures",
            "",
        ]
    )
    if not improved_failures:
        lines.append("No failing questions on the improved pipeline.")
    else:
        for row in improved_failures:
            lines.append(f"- `{row.id}` ({row.category}): {', '.join(row.failure_names())}")
    lines.extend(["", "## Naive failures the gate is there to catch", ""])
    lines.append(
        f"{len(naive_failures)} of {len(naive_rows)} naive questions fail a per-question check."
    )
    lines.append("")
    for name in OFFLINE_METRICS:
        count = sum(1 for row in naive_rows if name in row.failure_names())
        if count:
            ids = [row.id for row in naive_rows if name in row.failure_names()]
            preview = ", ".join(ids[:8])
            lines.append(f"- {name}: {count} questions ({preview})")
    lines.extend(
        [
            "",
            "## Live RAGAS metrics",
            "",
            "Not run. No OpenAI API key was available, so no judge scores are filled in.",
            "Live mode writes measured scores only after a real `northline-eval --mode live` run.",
            "",
            "Those metrics, when a key is present, are:",
            "",
        ]
    )
    for name in LIVE_METRICS:
        lines.append(f"- **{name}**: {DEFINITIONS[name]}")
    lines.append("")
    return "\n".join(lines)


def render_html(
    *,
    improved_scores: Mapping[str, float],
    naive_scores: Mapping[str, float],
    thresholds: Mapping[str, float],
    improved_rows: Sequence[QuestionScore],
    naive_rows: Sequence[QuestionScore],
    question_count: int,
    doc_count: int,
) -> str:
    improved_failures = [row for row in improved_rows if row.failure_names()]
    naive_failures = [row for row in naive_rows if row.failure_names()]
    rows_html: list[str] = []
    for name in OFFLINE_METRICS:
        improved = improved_scores[name]
        naive = naive_scores[name]
        threshold = thresholds[name]
        gate = "pass" if improved >= threshold else "fail"
        rows_html.append(
            "<tr>"
            f"<td>{_esc(name)}</td>"
            f"<td>{improved:.4f}</td>"
            f"<td>{naive:.4f}</td>"
            f"<td>{improved - naive:+.4f}</td>"
            f"<td>{threshold:.4f}</td>"
            f"<td>{gate}</td>"
            "</tr>"
        )
    if improved_failures:
        failure_items = []
        for row in improved_failures:
            names = _esc(", ".join(row.failure_names()))
            failure_items.append(
                f"<li><code>{_esc(row.id)}</code> ({_esc(row.category)}): {names}</li>"
            )
        failure_html = "".join(failure_items)
    else:
        failure_html = "<li>No failing questions on the improved pipeline.</li>"
    definitions = "".join(
        f"<li><strong>{_esc(name)}</strong>: {_esc(DEFINITIONS[name])}</li>"
        for name in OFFLINE_METRICS
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Northline docs eval report</title>
  <style>
    body {{ font-family: Georgia, serif; margin: 2rem auto; max-width: 920px; color: #1c1917; }}
    h1 {{ font-size: 1.6rem; }}
    table {{ border-collapse: collapse; width: 100%; font-family: sans-serif; }}
    th, td {{ border-bottom: 1px solid #d6d3d1; text-align: left; padding: 0.4rem 0.5rem; }}
    td:nth-child(n+2), th:nth-child(n+2) {{ text-align: right; }}
    code {{ font-family: ui-monospace, monospace; }}
    .note {{ background: #f5f5f4; padding: 0.8rem 1rem; }}
  </style>
</head>
<body>
  <h1>Northline docs eval report</h1>
  <p class="note">Offline scores from the deterministic pipeline. The corpus is synthetic.
  RAGAS model-judged metrics are not in this table. This run has no judge scores.</p>
  <p>Documents: {doc_count}. Questions: {question_count}.
  The gate applies to the improved column. Naive is the broken retriever with no guardrails.</p>
  <table>
    <thead>
      <tr><th>metric</th><th>improved</th><th>naive</th><th>delta</th><th>threshold</th><th>gate</th></tr>
    </thead>
    <tbody>
      {"".join(rows_html)}
    </tbody>
  </table>
  <h2>What the metrics mean</h2>
  <ul>{definitions}</ul>
  <h2>Improved per-question failures</h2>
  <ul>{failure_html}</ul>
  <h2>Naive failures</h2>
  <p>{len(naive_failures)} of {len(naive_rows)} naive questions fail a per-question check.</p>
</body>
</html>
"""


def write_png(
    path: Path,
    *,
    improved_scores: Mapping[str, float],
    naive_scores: Mapping[str, float],
    thresholds: Mapping[str, float],
) -> None:
    from PIL import Image, ImageDraw

    font = _font(18)
    small = _font(15)
    width = 1100
    row_height = 36
    height = 120 + row_height * (len(OFFLINE_METRICS) + 1)
    image = Image.new("RGB", (width, height), "#fafaf9")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, 64), fill="#1c1917")
    draw.text((24, 20), "Northline docs eval — offline gate", fill="#fafaf9", font=font)
    headers = ("metric", "improved", "naive", "threshold", "gate")
    columns = (24, 420, 560, 700, 880)
    y = 84
    for header, x in zip(headers, columns, strict=True):
        draw.text((x, y), header, fill="#44403c", font=small)
    y += row_height
    for name in OFFLINE_METRICS:
        improved = improved_scores[name]
        gate = "pass" if improved >= thresholds[name] else "fail"
        values = (
            name,
            f"{improved:.4f}",
            f"{naive_scores[name]:.4f}",
            f"{thresholds[name]:.4f}",
            gate,
        )
        color = "#166534" if gate == "pass" else "#991b1b"
        for value, x in zip(values, columns, strict=True):
            draw.text((x, y), value, fill=color if value == gate else "#1c1917", font=small)
        y += row_height
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")


def _font(size: int) -> Any:
    from PIL import ImageFont

    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )
