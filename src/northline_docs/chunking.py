from __future__ import annotations

from collections.abc import Sequence

from northline_docs.types import Chunk, Document


def chunk_documents(
    documents: Sequence[Document],
    *,
    max_chars: int = 4000,
    overlap: int = 200,
) -> list[Chunk]:
    if max_chars < 200:
        raise ValueError("max_chars must be at least 200")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap must be >= 0 and smaller than max_chars")
    chunks: list[Chunk] = []
    for document in documents:
        pieces = split_text(document.text, max_chars=max_chars, overlap=overlap)
        for index, piece in enumerate(pieces):
            chunk_id = document.doc_id if len(pieces) == 1 else f"{document.doc_id}#{index}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    doc_id=document.doc_id,
                    title=document.title,
                    version=document.version,
                    text=piece if piece.endswith("\n") else f"{piece}\n",
                    index=index,
                )
            )
    return chunks


def split_text(text: str, *, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    paragraphs = [part for part in text.split("\n\n") if part.strip()]
    pieces: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            pieces.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n\n{paragraph}" if tail else paragraph
            if len(current) > max_chars:
                pieces.append(current[:max_chars])
                current = current[max_chars - overlap :] if overlap else ""
        else:
            pieces.append(paragraph[:max_chars])
            current = paragraph[max_chars - overlap :] if overlap else ""
    if current:
        pieces.append(current)
    return pieces
