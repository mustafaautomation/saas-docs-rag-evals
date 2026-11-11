from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from northline_docs.guardrails import BEHAVIORS

_VERSIONS = frozenset({"v1", "v2"})


@dataclass(frozen=True)
class Question:
    id: str
    question: str
    reference: str
    reference_doc_ids: tuple[str, ...]
    must_include: tuple[str, ...]
    forbidden: tuple[str, ...]
    expected_behavior: str
    expected_version: str | None
    category: str
    retrieval_graded: bool


def load_questions(path: Path, *, known_doc_ids: set[str] | None = None) -> list[Question]:
    questions: list[Question] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise ValueError(f"{path}:{line_number} is not an object")
        question = _parse_question(raw, path, line_number, known_doc_ids)
        if question.id in seen:
            raise ValueError(f"Duplicate question id {question.id}")
        seen.add(question.id)
        questions.append(question)
    if not questions:
        raise ValueError(f"No questions in {path}")
    return questions


def _parse_question(
    raw: Mapping[str, object],
    path: Path,
    line_number: int,
    known_doc_ids: set[str] | None,
) -> Question:
    question_id = _required_str(raw, "id", path, line_number)
    behavior = _required_str(raw, "expected_behavior", path, line_number)
    if behavior not in BEHAVIORS:
        raise ValueError(f"{path}:{line_number} has unknown expected_behavior {behavior}")
    version = raw.get("expected_version")
    if version is not None and (not isinstance(version, str) or version not in _VERSIONS):
        raise ValueError(f"{path}:{line_number} has an invalid expected_version")
    doc_ids = _str_tuple(raw, "reference_doc_ids", path, line_number)
    if known_doc_ids is not None:
        missing = [doc_id for doc_id in doc_ids if doc_id not in known_doc_ids]
        if missing:
            raise ValueError(f"{path}:{line_number} references unknown docs {missing}")
    retrieval_graded = raw.get("retrieval_graded")
    if not isinstance(retrieval_graded, bool):
        raise ValueError(f"{path}:{line_number} retrieval_graded must be a boolean")
    if retrieval_graded and not doc_ids:
        raise ValueError(f"{path}:{line_number} is retrieval graded but has no reference docs")
    return Question(
        id=question_id,
        question=_required_str(raw, "question", path, line_number),
        reference=_required_str(raw, "reference", path, line_number),
        reference_doc_ids=doc_ids,
        must_include=_str_tuple(raw, "must_include", path, line_number),
        forbidden=_str_tuple(raw, "forbidden", path, line_number),
        expected_behavior=behavior,
        expected_version=version if isinstance(version, str) else None,
        category=_required_str(raw, "category", path, line_number),
        retrieval_graded=retrieval_graded,
    )


def _required_str(raw: Mapping[str, object], key: str, path: Path, line_number: int) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}:{line_number} field {key} must be a non-empty string")
    return value


def _str_tuple(
    raw: Mapping[str, object], key: str, path: Path, line_number: int
) -> tuple[str, ...]:
    value = raw.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{path}:{line_number} field {key} must be a list of strings")
    return tuple(value)
