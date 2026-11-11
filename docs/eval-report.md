# Northline docs eval report

Offline scores from the deterministic pipeline. The corpus is synthetic.
RAGAS faithfulness, answer relevancy, context precision, and context recall
are not in this table: they run only in live mode, and this run had no judge scores.

Documents: 22. Questions: 44.

The improved column is the version-filtered retriever with guardrails.
The naive column is the broken retriever and the prompt with no guardrails.
The gate applies to the improved column.

| metric | improved | naive | delta | threshold | gate |
| --- | ---: | ---: | ---: | ---: | --- |
| non_llm_context_recall | 1.0000 | 0.1000 | +0.9000 | 0.8000 | pass |
| string_presence | 1.0000 | 0.0909 | +0.9091 | 0.8000 | pass |
| refusal_correctness | 1.0000 | 0.6818 | +0.3182 | 1.0000 | pass |
| retrieval_hit_rate | 1.0000 | 0.1000 | +0.9000 | 0.8000 | pass |
| mrr | 1.0000 | 0.0611 | +0.9389 | 0.7000 | pass |
| endpoint_validity | 1.0000 | 0.9091 | +0.0909 | 1.0000 | pass |
| version_correctness | 1.0000 | 0.0000 | +1.0000 | 0.9000 | pass |

## What the metrics mean

- **non_llm_context_recall**: Whether the labelled source chunk was retrieved, using string similarity and no model.
- **string_presence**: Whether the answer contains the labelled facts from the docs.
- **refusal_correctness**: Whether secret requests, unknown endpoints, unknown parameters, and out-of-scope questions were handled as labelled.
- **retrieval_hit_rate**: Whether the labelled document appeared in the top results.
- **mrr**: How high the labelled document ranked. 1.0 means it was first.
- **endpoint_validity**: Whether every endpoint the answer mentions exists in the docs.
- **version_correctness**: Whether the answer stayed on the version the user asked about.

## Improved per-question failures

No failing questions on the improved pipeline.

## Naive failures the gate is there to catch

43 of 44 naive questions fail a per-question check.

- non_llm_context_recall: 27 questions (q01, q02, q03, q04, q05, q06, q07, q08)
- string_presence: 43 questions (q01, q02, q03, q04, q05, q06, q07, q08)
- refusal_correctness: 14 questions (q31, q32, q33, q34, q35, q36, q37, q38)
- retrieval_hit_rate: 27 questions (q01, q02, q03, q04, q05, q06, q07, q08)
- endpoint_validity: 4 questions (q35, q36, q37, q38)
- version_correctness: 24 questions (q01, q02, q03, q04, q05, q06, q07, q08)

## Live RAGAS metrics

Not run. No OpenAI API key was available, so no judge scores are filled in.
Live mode writes measured scores only after a real `northline-eval --mode live` run.

Those metrics, when a key is present, are:

- **faithfulness**: Whether the answer sticks to the retrieved documentation.
- **answer_relevancy**: Whether the answer addresses the question that was asked.
- **context_precision**: Whether higher-ranked chunks are the ones the reference needs.
- **context_recall**: Whether the retrieved chunks cover the claims in the reference answer.
