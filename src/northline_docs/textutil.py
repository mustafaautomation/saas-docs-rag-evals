from __future__ import annotations

import re

_TOKEN = re.compile(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", re.IGNORECASE)
_VERSION = re.compile(r"\bv([12])\b", re.IGNORECASE)

STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "to",
        "for",
        "in",
        "on",
        "and",
        "or",
        "is",
        "are",
        "was",
        "were",
        "be",
        "what",
        "how",
        "do",
        "does",
        "did",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
        "from",
        "by",
        "as",
        "at",
        "it",
        "this",
        "that",
        "i",
        "you",
        "we",
        "they",
        "my",
        "your",
        "our",
        "can",
        "if",
        "into",
        "about",
        "there",
        "their",
        "not",
        "no",
        "yes",
        "using",
        "use",
        "used",
        "please",
        "me",
        "should",
        "would",
        "could",
        "tell",
        "explain",
        "describe",
        "between",
        "than",
        "then",
        "so",
        "only",
        "also",
        "its",
        "per",
        "has",
        "have",
        "had",
        "been",
        "being",
        "am",
        "will",
        "just",
        "over",
        "under",
        "again",
        "once",
        "same",
        "other",
        "such",
        "own",
        "too",
        "very",
        "any",
        "all",
        "each",
        "both",
        "few",
        "more",
        "most",
        "some",
        "these",
        "those",
        "them",
        "his",
        "her",
        "she",
        "he",
        "but",
        "because",
        "while",
        "during",
        "before",
        "after",
        "above",
        "below",
        "up",
        "down",
        "out",
        "off",
    }
)


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN.finditer(text)]


def content_token_list(text: str) -> list[str]:
    tokens: list[str] = []
    for token in tokenize(text):
        if token in STOPWORDS:
            continue
        if len(token) <= 2 and token not in {"v1", "v2"}:
            continue
        tokens.append(token)
    return tokens


def content_overlap(question: str, text: str) -> float:
    query_tokens = set(content_token_list(question))
    if not query_tokens:
        return 0.0
    document_tokens = set(content_token_list(text))
    return len(query_tokens & document_tokens) / len(query_tokens)


def detect_version(question: str) -> str | None:
    found = {match.group(1) for match in _VERSION.finditer(question)}
    if found == {"1"}:
        return "v1"
    if found == {"2"}:
        return "v2"
    return None


def versions_for(version: str | None) -> set[str] | None:
    if version is None:
        return None
    return {version, "shared"}
