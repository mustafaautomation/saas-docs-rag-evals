from __future__ import annotations

from northline_docs.chunking import chunk_documents, split_text
from northline_docs.eval.dataset import Question
from northline_docs.guardrails import contains_secret_value
from northline_docs.runtime import Runtime


def test_corpus_is_synthetic_and_in_range(runtime: Runtime) -> None:
    assert 15 <= len(runtime.documents) <= 30
    versions = {document.version for document in runtime.documents}
    assert versions == {"shared", "v1", "v2"}
    overview = runtime.chunks_by_id["overview"].text.lower()
    assert "fictional" in overview
    assert "synthetic" in overview
    for document in runtime.documents:
        assert not contains_secret_value(document.text)


def test_each_current_doc_is_one_chunk(runtime: Runtime) -> None:
    assert len(runtime.chunks) == len(runtime.documents)
    assert {chunk.doc_id for chunk in runtime.chunks} == {
        document.doc_id for document in runtime.documents
    }


def test_chunker_splits_a_long_document(runtime: Runtime) -> None:
    document = runtime.documents[0]
    long_body = "\n\n".join(f"Paragraph {index} about pagination cursors." for index in range(80))
    replacement = type(document)(
        doc_id=document.doc_id,
        title=document.title,
        version=document.version,
        body=long_body,
        text=f"{document.title}\n\n{long_body}\n",
        source_path=document.source_path,
    )
    pieces = split_text(replacement.text, max_chars=500, overlap=40)
    assert len(pieces) > 1
    chunks = chunk_documents([replacement], max_chars=500, overlap=40)
    assert len(chunks) == len(pieces)
    assert chunks[0].chunk_id == f"{document.doc_id}#0"


def test_question_set_covers_guardrails(questions: list[Question]) -> None:
    assert 30 <= len(questions) <= 50
    behaviors = {question.expected_behavior for question in questions}
    assert behaviors == {
        "answer",
        "refuse_secret",
        "refuse_unknown_endpoint",
        "refuse_unknown_parameter",
        "unknown",
    }
    versions = {question.expected_version for question in questions}
    assert "v1" in versions
    assert "v2" in versions
    graded = [question for question in questions if question.retrieval_graded]
    assert len(graded) >= 20
    assert all(question.reference_doc_ids for question in graded)


def test_catalog_matches_documented_endpoints(runtime: Runtime) -> None:
    known = set(runtime.catalog.known_endpoints())
    assert "POST /v1/customers" in known
    assert "POST /v2/invoices/{}/issue" in known
    assert runtime.catalog.unknown_endpoints("How do I call POST /v1/refunds?") == [
        "POST /v1/refunds"
    ]
    purge = "What parameters does DELETE /v2/customers/{customer_id}/purge accept?"
    assert runtime.catalog.unknown_endpoints(purge)
    for document in runtime.documents:
        assert runtime.catalog.unknown_endpoints(document.text) == []
