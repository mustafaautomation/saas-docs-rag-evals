from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from northline_docs.types import Document

_METHOD_PATH = re.compile(
    r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/v[12]/[A-Za-z0-9_{}/-]+)",
    re.IGNORECASE,
)
_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,}")


def normalize_path(path: str) -> str:
    trimmed = path.rstrip(".,);\"'`")
    parts = [part for part in trimmed.split("/") if part]
    normalized = ["{}" if part.startswith("{") and part.endswith("}") else part for part in parts]
    return "/" + "/".join(normalized)


@dataclass(frozen=True)
class EndpointCatalog:
    """HTTP methods and paths extracted from the docs. Nothing is added by hand."""

    methods_by_path: dict[str, frozenset[str]]

    @classmethod
    def from_documents(cls, documents: Sequence[Document]) -> EndpointCatalog:
        found: dict[str, set[str]] = {}
        for document in documents:
            for method, path in _iter_endpoints(document.text):
                found.setdefault(normalize_path(path), set()).add(method)
        return cls(methods_by_path={path: frozenset(methods) for path, methods in found.items()})

    def known_endpoints(self) -> list[str]:
        rows: list[str] = []
        for path in sorted(self.methods_by_path):
            for method in sorted(self.methods_by_path[path]):
                rows.append(f"{method} {path}")
        return rows

    def unknown_endpoints(self, text: str) -> list[str]:
        unknown: list[str] = []
        seen: set[str] = set()
        for method, path in _iter_endpoints(text):
            display = f"{method} {path.rstrip('.,);')}"
            if display in seen:
                continue
            seen.add(display)
            methods = self.methods_by_path.get(normalize_path(path), frozenset())
            if method not in methods:
                unknown.append(display)
        return unknown


def corpus_identifiers(documents: Iterable[Document]) -> frozenset[str]:
    names: set[str] = set()
    for document in documents:
        names.update(match.group(0).lower() for match in _IDENTIFIER.finditer(document.text))
    return frozenset(names)


def _iter_endpoints(text: str) -> list[tuple[str, str]]:
    return [(match.group(1).upper(), match.group(2)) for match in _METHOD_PATH.finditer(text)]
