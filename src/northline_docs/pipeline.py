from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from northline_docs.catalog import EndpointCatalog
from northline_docs.guardrails import (
    NAIVE_LEAK,
    SECRET_REFUSAL,
    UNKNOWN_REFUSAL,
    apply_post_checks,
    asks_for_secret,
    classify_response,
    endpoint_refusal,
    parameter_refusal,
    unknown_parameters,
)
from northline_docs.textutil import content_overlap, detect_version, versions_for
from northline_docs.types import Answer, ScoredChunk


class Retriever(Protocol):
    def search(self, query: str, k: int, versions: set[str] | None) -> list[ScoredChunk]: ...


class Generator(Protocol):
    def generate(self, question: str, contexts: Sequence[str], version: str | None) -> str: ...


class RagPipeline:
    def __init__(
        self,
        *,
        retriever: Retriever,
        generator: Generator,
        catalog: EndpointCatalog,
        identifiers: frozenset[str],
        top_k: int,
        overlap_threshold: float,
        guardrails_enabled: bool,
        variant: str,
    ) -> None:
        self._retriever = retriever
        self._generator = generator
        self._catalog = catalog
        self._identifiers = identifiers
        self._top_k = top_k
        self._overlap_threshold = overlap_threshold
        self._guardrails_enabled = guardrails_enabled
        self.variant = variant

    def answer(self, question: str) -> Answer:
        version = detect_version(question)
        unknown_endpoints = self._catalog.unknown_endpoints(question)
        missing_params = unknown_parameters(question, self._identifiers)
        secret = asks_for_secret(question)

        if self._guardrails_enabled:
            if secret:
                return self._finish(question, SECRET_REFUSAL, (), version, "refuse_secret")
            if unknown_endpoints:
                text = endpoint_refusal(unknown_endpoints[0])
                return self._finish(question, text, (), version, "refuse_unknown_endpoint")
            if missing_params:
                text = parameter_refusal(missing_params[0])
                return self._finish(question, text, (), version, "refuse_unknown_parameter")

        version_filter = versions_for(version) if self._guardrails_enabled else None
        retrieved = tuple(self._retriever.search(question, self._top_k, version_filter))

        if not self._guardrails_enabled and secret:
            return self._finish(question, NAIVE_LEAK, retrieved, None, "answer")

        if self._guardrails_enabled:
            overlap = content_overlap(question, retrieved[0].chunk.text) if retrieved else 0.0
            if overlap < self._overlap_threshold:
                return self._finish(question, UNKNOWN_REFUSAL, retrieved, version, "unknown")
            response = self._generator.generate(question, [retrieved[0].chunk.text], version)
            response = apply_post_checks(response, self._catalog)
            return self._finish(question, response, retrieved, version, classify_response(response))

        contexts = [retrieved[0].chunk.text] if retrieved else []
        if contexts:
            response = self._generator.generate(question, contexts, None)
        else:
            response = UNKNOWN_REFUSAL
        if unknown_endpoints:
            response = f"{response}\n\nCall {unknown_endpoints[0]} with the fields the user named."
        if missing_params:
            response = f"{response}\n\nSet the `{missing_params[0]}` parameter as requested."
        return self._finish(question, response, retrieved, None, classify_response(response))

    def _finish(
        self,
        question: str,
        response: str,
        retrieved: tuple[ScoredChunk, ...],
        version: str | None,
        behavior: str,
    ) -> Answer:
        return Answer(
            question=question,
            response=response,
            retrieved=retrieved,
            version=version,
            behavior=behavior,
            variant=self.variant,
        )
