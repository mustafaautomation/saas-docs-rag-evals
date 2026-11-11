from __future__ import annotations

import asyncio
import math
import os
from collections.abc import Sequence
from typing import Any

from northline_docs.eval.records import Record
from northline_docs.runtime import LIVE_METRICS


class LiveEvalUnavailable(RuntimeError):
    pass


def require_openai_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise LiveEvalUnavailable(
            "OPENAI_API_KEY is not set. Live RAGAS metrics were not run. "
            "Offline mode does not need a key."
        )
    return key


def ragas_metric_names() -> tuple[str, ...]:
    return LIVE_METRICS


async def score_with_ragas(
    records: Sequence[Record],
    *,
    api_key: str,
    chat_model: str,
    embedding_model: str,
) -> dict[str, float]:
    """Run the current RAGAS collections metrics. This calls OpenAI and is live-only."""
    from openai import AsyncOpenAI
    from ragas.embeddings.base import embedding_factory
    from ragas.llms import llm_factory
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )

    client = AsyncOpenAI(api_key=api_key)
    llm = llm_factory(chat_model, client=client)
    embeddings: Any = embedding_factory("openai", model=embedding_model, client=client)
    faithfulness = Faithfulness(llm=llm)
    relevancy = AnswerRelevancy(llm=llm, embeddings=embeddings)
    precision = ContextPrecision(llm=llm)
    recall = ContextRecall(llm=llm)

    totals = {name: 0.0 for name in LIVE_METRICS}
    if not records:
        raise ValueError("No records to judge")
    for record in records:
        contexts = list(record.retrieved_contexts) or ["(no documentation retrieved)"]
        faith = await faithfulness.ascore(
            user_input=record.question,
            response=record.response,
            retrieved_contexts=contexts,
        )
        answer_relevancy = await relevancy.ascore(
            user_input=record.question,
            response=record.response,
        )
        context_precision = await precision.ascore(
            user_input=record.question,
            reference=record.reference,
            retrieved_contexts=contexts,
        )
        context_recall = await recall.ascore(
            user_input=record.question,
            reference=record.reference,
            retrieved_contexts=contexts,
        )
        totals["faithfulness"] += _metric_value(faith)
        totals["answer_relevancy"] += _metric_value(answer_relevancy)
        totals["context_precision"] += _metric_value(context_precision)
        totals["context_recall"] += _metric_value(context_recall)
    count = float(len(records))
    return {name: totals[name] / count for name in LIVE_METRICS}


def score_with_ragas_sync(
    records: Sequence[Record],
    *,
    api_key: str,
    chat_model: str,
    embedding_model: str,
) -> dict[str, float]:
    return asyncio.run(
        score_with_ragas(
            records,
            api_key=api_key,
            chat_model=chat_model,
            embedding_model=embedding_model,
        )
    )


def _metric_value(result: object) -> float:
    raw = getattr(result, "value", None)
    if raw is None:
        raise RuntimeError("RAGAS metric result has no value")
    number = float(raw)
    if math.isnan(number):
        return 0.0
    return number
