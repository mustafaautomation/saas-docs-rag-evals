from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from northline_docs.eval.dataset import Question
from northline_docs.pipeline import RagPipeline
from northline_docs.types import Chunk


@dataclass(frozen=True)
class Record:
    id: str
    question: str
    response: str
    retrieved_doc_ids: tuple[str, ...]
    retrieved_contexts: tuple[str, ...]
    reference: str
    reference_doc_ids: tuple[str, ...]
    reference_contexts: tuple[str, ...]
    must_include: tuple[str, ...]
    forbidden: tuple[str, ...]
    expected_behavior: str
    expected_version: str | None
    category: str
    retrieval_graded: bool
    variant: str

    def to_json(self) -> dict[str, object]:
        return {
            "id": self.id,
            "question": self.question,
            "response": self.response,
            "retrieved_doc_ids": list(self.retrieved_doc_ids),
            "retrieved_contexts": list(self.retrieved_contexts),
            "reference": self.reference,
            "reference_doc_ids": list(self.reference_doc_ids),
            "reference_contexts": list(self.reference_contexts),
            "must_include": list(self.must_include),
            "forbidden": list(self.forbidden),
            "expected_behavior": self.expected_behavior,
            "expected_version": self.expected_version,
            "category": self.category,
            "retrieval_graded": self.retrieval_graded,
            "variant": self.variant,
        }


class SnapshotStale(RuntimeError):
    pass


def run_questions(
    pipeline: RagPipeline,
    questions: list[Question],
    chunks_by_id: dict[str, Chunk],
) -> list[Record]:
    records: list[Record] = []
    for question in questions:
        answer = pipeline.answer(question.question)
        reference_contexts = tuple(
            chunks_by_id[doc_id].text for doc_id in question.reference_doc_ids
        )
        records.append(
            Record(
                id=question.id,
                question=question.question,
                response=answer.response,
                retrieved_doc_ids=tuple(hit.chunk.doc_id for hit in answer.retrieved),
                retrieved_contexts=tuple(hit.chunk.text for hit in answer.retrieved),
                reference=question.reference,
                reference_doc_ids=question.reference_doc_ids,
                reference_contexts=reference_contexts,
                must_include=question.must_include,
                forbidden=question.forbidden,
                expected_behavior=question.expected_behavior,
                expected_version=question.expected_version,
                category=question.category,
                retrieval_graded=question.retrieval_graded,
                variant=pipeline.variant,
            )
        )
    return records


def write_jsonl(path: Path, records: list[Record]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record.to_json(), ensure_ascii=False, sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[Record]:
    records: list[Record] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise ValueError(f"{path}:{line_number} is not an object")
        records.append(_parse_record(raw, path, line_number))
    if not records:
        raise ValueError(f"No records in {path}")
    return records


def assert_snapshot_current(records: list[Record], chunks_by_id: Mapping[str, Chunk]) -> None:
    for record in records:
        if len(record.retrieved_doc_ids) != len(record.retrieved_contexts):
            raise SnapshotStale(f"{record.id} has mismatched retrieved ids and contexts")
        for doc_id, text in zip(record.retrieved_doc_ids, record.retrieved_contexts, strict=True):
            current = chunks_by_id.get(doc_id)
            if current is None or current.text != text:
                raise SnapshotStale(
                    f"Snapshot for {record.id} is stale at doc {doc_id}. "
                    "Run `uv run northline-eval --refresh-snapshot`."
                )
        for doc_id, text in zip(record.reference_doc_ids, record.reference_contexts, strict=True):
            current = chunks_by_id.get(doc_id)
            if current is None or current.text != text:
                raise SnapshotStale(
                    f"Snapshot reference context for {record.id} does not match {doc_id}."
                )


def _parse_record(raw: Mapping[str, object], path: Path, line_number: int) -> Record:
    version = raw.get("expected_version")
    if version is not None and not isinstance(version, str):
        raise ValueError(f"{path}:{line_number} expected_version is invalid")
    retrieval_graded = raw.get("retrieval_graded")
    if not isinstance(retrieval_graded, bool):
        raise ValueError(f"{path}:{line_number} retrieval_graded must be a boolean")
    return Record(
        id=_string(raw, "id", path, line_number),
        question=_string(raw, "question", path, line_number),
        response=_string(raw, "response", path, line_number),
        retrieved_doc_ids=_strings(raw, "retrieved_doc_ids", path, line_number),
        retrieved_contexts=_strings(raw, "retrieved_contexts", path, line_number),
        reference=_string(raw, "reference", path, line_number),
        reference_doc_ids=_strings(raw, "reference_doc_ids", path, line_number),
        reference_contexts=_strings(raw, "reference_contexts", path, line_number),
        must_include=_strings(raw, "must_include", path, line_number),
        forbidden=_strings(raw, "forbidden", path, line_number),
        expected_behavior=_string(raw, "expected_behavior", path, line_number),
        expected_version=version if isinstance(version, str) else None,
        category=_string(raw, "category", path, line_number),
        retrieval_graded=retrieval_graded,
        variant=_string(raw, "variant", path, line_number),
    )


def _string(raw: Mapping[str, object], key: str, path: Path, line_number: int) -> str:
    value = raw.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{path}:{line_number} field {key} must be a string")
    return value


def _strings(raw: Mapping[str, object], key: str, path: Path, line_number: int) -> tuple[str, ...]:
    value = raw.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{path}:{line_number} field {key} must be a list of strings")
    return tuple(value)
