from __future__ import annotations

import re
from pathlib import Path

from northline_docs.types import Document

_FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)
_VERSIONS = frozenset({"shared", "v1", "v2"})


def load_corpus(corpus_dir: Path) -> list[Document]:
    paths = sorted(corpus_dir.glob("*.md"))
    if not paths:
        raise FileNotFoundError(f"No markdown documents in {corpus_dir}")
    documents = [_parse_document(path) for path in paths]
    ids = [document.doc_id for document in documents]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate document ids in corpus")
    return documents


def _parse_document(path: Path) -> Document:
    raw = path.read_text(encoding="utf-8")
    match = _FRONT_MATTER.match(raw)
    if match is None:
        raise ValueError(f"Missing front matter in {path}")
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"Invalid front matter line in {path}: {line}")
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    doc_id = meta.get("id", "")
    title = meta.get("title", "")
    version = meta.get("version", "")
    if not doc_id or not title or version not in _VERSIONS:
        raise ValueError(f"Front matter id/title/version is incomplete in {path}")
    if doc_id != path.stem:
        raise ValueError(f"Document id {doc_id} does not match filename {path.name}")
    body = match.group(2).strip()
    text = f"{title}\n\n{body}\n"
    return Document(
        doc_id=doc_id,
        title=title,
        version=version,
        body=body,
        text=text,
        source_path=str(path),
    )
