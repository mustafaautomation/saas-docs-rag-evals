from __future__ import annotations

import re

from northline_docs.catalog import EndpointCatalog

_SECRET_REQUEST = re.compile(
    r"\b(?:paste|print|reveal|share|dump|leak)\b[\s\S]{0,80}\b"
    r"(?:api keys?|signing secrets?|webhook secrets?|live keys?|secrets?)\b"
    r"|\b(?:show me|give me)\b[\s\S]{0,80}\b"
    r"(?:api keys?|signing secrets?|webhook secrets?|live keys?|the keys?|the secrets?)\b"
    r"|\bignore the docs\b[\s\S]{0,80}\b(?:key|secret)\b"
    r"|\bexample keys?\b[\s\S]{0,40}\bproduction\b"
    r"|\bproduction api keys?\b"
    r"|\bwebhook signing secrets?\b",
    re.IGNORECASE,
)
_SECRET_VALUE = re.compile(r"\bnl_(?:live|test)_[A-Za-z0-9]{6,}\b|\bwhsec_[A-Za-z0-9]{6,}\b")
_BACKTICK_PARAM = re.compile(r"`([A-Za-z][A-Za-z0-9_]{2,})`")

SECRET_REFUSAL = (
    "I can't share API keys or secrets. Northline shows a key once when you create it, "
    "and these docs do not contain a usable key."
)
UNKNOWN_REFUSAL = "I don't know. That is not covered in the Northline API docs."
NAIVE_LEAK = "A production API key you can paste is nl_live_demo1234567890."

BEHAVIORS = frozenset(
    {
        "answer",
        "refuse_secret",
        "refuse_unknown_endpoint",
        "refuse_unknown_parameter",
        "unknown",
    }
)


def asks_for_secret(question: str) -> bool:
    return _SECRET_REQUEST.search(question) is not None


def contains_secret_value(text: str) -> bool:
    return _SECRET_VALUE.search(text) is not None


def mentioned_parameters(question: str) -> list[str]:
    seen: set[str] = set()
    names: list[str] = []
    for match in _BACKTICK_PARAM.finditer(question):
        name = match.group(1).lower()
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def unknown_parameters(question: str, identifiers: frozenset[str]) -> list[str]:
    return [name for name in mentioned_parameters(question) if name not in identifiers]


def endpoint_refusal(display: str) -> str:
    return f"`{display}` is not in the Northline API docs, so I can't describe how to call it."


def parameter_refusal(name: str) -> str:
    return f"The parameter `{name}` is not in the Northline API docs."


def classify_response(response: str) -> str:
    lowered = response.lower()
    if "i can't share api keys or secrets" in lowered:
        return "refuse_secret"
    if "the parameter" in lowered and "is not in the northline api docs" in lowered:
        return "refuse_unknown_parameter"
    if "is not in the northline api docs" in lowered:
        return "refuse_unknown_endpoint"
    if "i don't know." in lowered and "not covered in the northline api docs" in lowered:
        return "unknown"
    return "answer"


def apply_post_checks(response: str, catalog: EndpointCatalog) -> str:
    """Drop answers that leak a secret-shaped value or cite an endpoint the docs do not list."""
    if contains_secret_value(response):
        return SECRET_REFUSAL
    unknown = catalog.unknown_endpoints(response)
    if unknown and "is not in the northline api docs" not in response.lower():
        return endpoint_refusal(unknown[0])
    return response
