from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    override = os.environ.get("NORTHLINE_ROOT")
    if override:
        return Path(override).resolve()
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pyproject.toml").is_file() and (candidate / "corpus").is_dir():
            return candidate
    raise FileNotFoundError(
        "Could not locate the repository root from NORTHLINE_ROOT or pyproject.toml"
    )
