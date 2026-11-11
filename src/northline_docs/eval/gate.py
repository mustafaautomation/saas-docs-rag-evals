from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class GateResult:
    passed: bool
    failures: tuple[str, ...]
    scores: dict[str, float]


def apply_gate(scores: Mapping[str, float], thresholds: Mapping[str, float]) -> GateResult:
    failures: list[str] = []
    for name, threshold in thresholds.items():
        score = scores.get(name)
        if score is None:
            failures.append(f"{name}: missing score")
        elif score < threshold:
            failures.append(f"{name}: {score:.4f} < {threshold:.4f}")
    return GateResult(passed=not failures, failures=tuple(failures), scores=dict(scores))
