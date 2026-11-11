from __future__ import annotations

from pathlib import Path


def test_readme_is_factual_about_the_demo(root: Path) -> None:
    text = (root / "README.md").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "synthetic" in lowered
    assert "1.0000" in text
    assert "0.0611" in text
    assert "production-ready" not in lowered
    assert "blazing" not in lowered
    assert "respond.io" not in lowered
    assert "illustrative_example_not_a_measurement" in text
