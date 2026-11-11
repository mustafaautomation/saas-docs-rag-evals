from __future__ import annotations

import asyncio
import warnings
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from northline_docs.eval.records import Record
from northline_docs.guardrails import classify_response
from northline_docs.runtime import OFFLINE_METRICS


@dataclass(frozen=True)
class QuestionScore:
    id: str
    category: str
    string_presence: float
    refusal_correctness: float
    endpoint_validity: float
    version_correctness: float | None
    hit: float | None
    reciprocal_rank: float | None
    non_llm_context_recall: float | None

    def failure_names(self) -> list[str]:
        failures: list[str] = []
        if self.string_presence < 1.0:
            failures.append("string_presence")
        if self.refusal_correctness < 1.0:
            failures.append("refusal_correctness")
        if self.endpoint_validity < 1.0:
            failures.append("endpoint_validity")
        if self.version_correctness == 0.0:
            failures.append("version_correctness")
        if self.hit == 0.0:
            failures.append("retrieval_hit_rate")
        if self.non_llm_context_recall == 0.0:
            failures.append("non_llm_context_recall")
        return failures


def score_records(
    records: Sequence[Record],
    *,
    catalog_unknown: Callable[[str], list[str]],
    chunk_versions: Mapping[str, str],
) -> tuple[dict[str, float], list[QuestionScore]]:
    recall_by_id = _non_llm_context_recall(records)
    rows: list[QuestionScore] = []
    for record in records:
        hit, reciprocal = _retrieval_scores(record)
        version_score = _version_score(record, chunk_versions)
        rows.append(
            QuestionScore(
                id=record.id,
                category=record.category,
                string_presence=_string_presence(record.response, record.must_include),
                refusal_correctness=float(
                    classify_response(record.response) == record.expected_behavior
                ),
                endpoint_validity=_endpoint_validity(record.response, catalog_unknown),
                version_correctness=version_score,
                hit=hit,
                reciprocal_rank=reciprocal,
                non_llm_context_recall=recall_by_id.get(record.id),
            )
        )
    aggregate = {
        "string_presence": _mean([row.string_presence for row in rows]),
        "refusal_correctness": _mean([row.refusal_correctness for row in rows]),
        "endpoint_validity": _mean([row.endpoint_validity for row in rows]),
        "version_correctness": _mean(
            [row.version_correctness for row in rows if row.version_correctness is not None]
        ),
        "retrieval_hit_rate": _mean([row.hit for row in rows if row.hit is not None]),
        "mrr": _mean([row.reciprocal_rank for row in rows if row.reciprocal_rank is not None]),
        "non_llm_context_recall": _mean(
            [row.non_llm_context_recall for row in rows if row.non_llm_context_recall is not None]
        ),
    }
    missing = [name for name in OFFLINE_METRICS if name not in aggregate]
    if missing:
        raise RuntimeError(f"Metrics did not produce {missing}")
    return aggregate, rows


def _string_presence(response: str, phrases: Sequence[str]) -> float:
    if not phrases:
        return 1.0
    lowered = response.lower()
    found = sum(1 for phrase in phrases if phrase.lower() in lowered)
    return found / len(phrases)


def _endpoint_validity(response: str, catalog_unknown: Callable[[str], list[str]]) -> float:
    if "is not in the northline api docs" in response.lower():
        return 1.0
    return 0.0 if catalog_unknown(response) else 1.0


def _retrieval_scores(record: Record) -> tuple[float | None, float | None]:
    if not record.retrieval_graded:
        return None, None
    references = set(record.reference_doc_ids)
    for rank, doc_id in enumerate(record.retrieved_doc_ids, start=1):
        if doc_id in references:
            return 1.0, 1.0 / rank
    return 0.0, 0.0


def _version_score(record: Record, chunk_versions: Mapping[str, str]) -> float | None:
    if record.expected_behavior != "answer" or record.expected_version is None:
        return None
    lowered = record.response.lower()
    if any(phrase.lower() in lowered for phrase in record.forbidden):
        return 0.0
    other = "v1" if record.expected_version == "v2" else "v2"
    retrieved_versions = {chunk_versions.get(doc_id, "") for doc_id in record.retrieved_doc_ids}
    if other in retrieved_versions:
        return 0.0
    if not set(record.reference_doc_ids).intersection(record.retrieved_doc_ids):
        return 0.0
    return 1.0


def _mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("Cannot average an empty metric")
    return sum(values) / len(values)


def _non_llm_context_recall(records: Sequence[Record]) -> dict[str, float]:
    graded = [record for record in records if record.retrieval_graded]
    if not graded:
        return {}

    async def _run() -> list[float]:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from ragas.dataset_schema import SingleTurnSample
            from ragas.metrics import NonLLMContextRecall

        metric = NonLLMContextRecall()
        scores: list[float] = []
        for record in graded:
            if not record.retrieved_contexts or not record.reference_contexts:
                scores.append(0.0)
                continue
            sample = SingleTurnSample(
                retrieved_contexts=list(record.retrieved_contexts),
                reference_contexts=list(record.reference_contexts),
            )
            scores.append(float(await metric.single_turn_ascore(sample)))
        return scores

    values = asyncio.run(_run())
    return {record.id: score for record, score in zip(graded, values, strict=True)}
