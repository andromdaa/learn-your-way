"""Unit tests for SourceFaithfulnessValidator and span_is_contained."""

from __future__ import annotations

from lesson_graph.models import ConceptNode, LessonGraph, SourceSpan
from lyw_core.validators.faithfulness import (
    ItemValidationPayload,
    SourceFaithfulnessValidator,
    span_is_contained,
)


def _span(
    doc_id: str = "doc-1",
    page_start: int = 1,
    page_end: int = 1,
    char_start: int = 0,
    char_end: int = 100,
) -> SourceSpan:
    return SourceSpan(
        doc_id=doc_id,
        page_start=page_start,
        page_end=page_end,
        char_start=char_start,
        char_end=char_end,
    )


def _graph(concept_spans: list[SourceSpan]) -> LessonGraph:
    return LessonGraph(
        id="g1",
        source_id="src-1",
        concepts=[
            ConceptNode(
                id="c1",
                title="t",
                summary="s",
                learning_objective="lo",
                source_spans=concept_spans,
            )
        ],
    )


def test_span_is_contained_true_when_within() -> None:
    concept = _span(char_start=0, char_end=200)
    item = _span(char_start=10, char_end=50)
    assert span_is_contained(item, [concept]) is True


def test_span_is_contained_false_when_doc_id_differs() -> None:
    concept = _span(doc_id="A")
    item = _span(doc_id="B")
    assert span_is_contained(item, [concept]) is False


def test_span_is_contained_false_when_chars_outside() -> None:
    concept = _span(char_start=0, char_end=50)
    item = _span(char_start=60, char_end=80)
    assert span_is_contained(item, [concept]) is False


def test_span_is_contained_false_when_pages_disjoint() -> None:
    concept = _span(page_start=1, page_end=2)
    item = _span(page_start=5, page_end=5)
    assert span_is_contained(item, [concept]) is False


def test_validator_passes_when_span_within_concept() -> None:
    validator = SourceFaithfulnessValidator()
    graph = _graph([_span(char_start=0, char_end=200)])
    payload = ItemValidationPayload(
        concept_id="c1",
        spans=[_span(char_start=20, char_end=40)],
        lesson_graph=graph,
    )
    result = validator.validate(payload)
    assert result.passed is True


def test_validator_fails_when_concept_id_unknown() -> None:
    validator = SourceFaithfulnessValidator()
    graph = _graph([_span()])
    payload = ItemValidationPayload(
        concept_id="no-such-concept",
        spans=[_span()],
        lesson_graph=graph,
    )
    result = validator.validate(payload)
    assert result.passed is False
    assert result.reason is not None
    assert "no-such-concept" in result.reason


def test_validator_fails_when_span_outside_concept() -> None:
    validator = SourceFaithfulnessValidator()
    graph = _graph([_span(char_start=0, char_end=50)])
    bad = _span(char_start=100, char_end=200)
    payload = ItemValidationPayload(
        concept_id="c1",
        spans=[bad],
        lesson_graph=graph,
    )
    result = validator.validate(payload)
    assert result.passed is False
    assert result.evidence == [bad]
