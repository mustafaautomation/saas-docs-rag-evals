from __future__ import annotations

from collections.abc import Sequence


class ExtractiveGenerator:
    """Quotes the retrieved documentation. Deterministic, and it does not call a model."""

    def generate(self, question: str, contexts: Sequence[str], version: str | None) -> str:
        del question
        if version is None:
            header = "The Northline docs say:"
        else:
            header = f"For API version {version}, the Northline docs say:"
        if not contexts:
            return header
        body = "\n\n".join(context.strip() for context in contexts)
        return f"{header}\n\n{body}"
