from __future__ import annotations

from pathlib import Path

import pytest

from northline_docs.eval.dataset import Question, load_questions
from northline_docs.paths import repo_root
from northline_docs.runtime import Runtime, load_runtime


@pytest.fixture(scope="session")
def root() -> Path:
    return repo_root()


@pytest.fixture(scope="session")
def runtime() -> Runtime:
    return load_runtime()


@pytest.fixture(scope="session")
def questions(runtime: Runtime) -> list[Question]:
    return load_questions(
        runtime.root / "evals" / "questions.jsonl",
        known_doc_ids=set(runtime.chunks_by_id),
    )
