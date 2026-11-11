from __future__ import annotations

import pytest

from northline_docs.eval.cli import main


def test_offline_eval_passes() -> None:
    assert main(["--mode", "offline", "--no-write-report"]) == 0


def test_naive_eval_fails_the_gate() -> None:
    assert main(["--mode", "offline", "--variant", "naive", "--no-write-report"]) == 1


def test_live_eval_without_a_key_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert main(["--mode", "live", "--no-write-report"]) == 2
