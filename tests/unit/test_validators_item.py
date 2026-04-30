"""Unit tests for SourceFaithfulnessValidator and ClarityValidator."""

import pytest

from lesson_graph.models import AssessmentItem, ConceptNode, LessonGraph, SourceSpan
from lyw_core.validators.clarity import ClarityValidator
from lyw_core.validators.faithfulness import (
    ItemValidationPayload,
    SourceFaithfulnessValidator,
    span_is_contained,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _span(
    doc_id: str = "doc-1",
    page_start: int = 1,
    page_end: int = 2,
    char_start: int = 0,
    char_end: int = 500,
) -> SourceSpan:
    return SourceSpan(
        doc_id=doc_id,
        page_start=page_start,
        page_end=page_end,
        char_start=char_start,
        char_end=char_end,
    )


def _concept(
    id: str = "c1",
    learning_objective: str = "Understand photosynthesis.",
    spans: list[SourceSpan] | None = None,
) -> ConceptNode:
    return ConceptNode(
        id=id,
        title="Photosynthesis",
        summary="Plants make food from light.",
        learning_objective=learning_objective,
        source_spans=spans or [_span()],
    )


def _item(
    concept_id: str = "c1",
    spans: list[SourceSpan] | None = None,
) -> AssessmentItem:
    return AssessmentItem(
        id="q1",
        kind="mcq",
        prompt="What is photosynthesis?",
        rationale="Covered in source.",
        source_spans=spans or [_span(char_start=10, char_end=100)],
        difficulty="easy",
        concept_id=concept_id,
    )


def _graph(concepts: list[ConceptNode] | None = None) -> LessonGraph:
    return LessonGraph(
        id="g1",
        source_id="doc-1",
        concepts=concepts or [_concept()],
    )


def _payload(
    item: AssessmentItem | None = None,
    graph: LessonGraph | None = None,
) -> ItemValidationPayload:
    return ItemValidationPayload(item=item or _item(), lesson_graph=graph or _graph())


# ---------------------------------------------------------------------------
# span_is_contained helper
# ---------------------------------------------------------------------------


def test_span_contained_within_concept_span() -> None:
    item_span = _span(char_start=50, char_end=200)
    concept_spans = [_span(char_start=0, char_end=500)]
    assert span_is_contained(item_span, concept_spans) is True


def test_span_not_contained_outside_char_range() -> None:
    item_span = _span(char_start=0, char_end=600)
    concept_spans = [_span(char_start=0, char_end=500)]
    assert span_is_contained(item_span, concept_spans) is False


def test_span_not_contained_different_doc() -> None:
    item_span = _span(doc_id="doc-2", char_start=0, char_end=100)
    concept_spans = [_span(doc_id="doc-1", char_start=0, char_end=500)]
    assert span_is_contained(item_span, concept_spans) is False


def test_span_contained_via_any_concept_span() -> None:
    item_span = _span(char_start=600, char_end=700)
    concept_spans = [
        _span(char_start=0, char_end=500),
        _span(char_start=500, char_end=800),
    ]
    assert span_is_contained(item_span, concept_spans) is True


# ---------------------------------------------------------------------------
# SourceFaithfulnessValidator
# ---------------------------------------------------------------------------


def test_faithfulness_passes_for_contained_span() -> None:
    result = SourceFaithfulnessValidator().validate(_payload())
    assert result.passed is True
    assert result.evidence is None


def test_faithfulness_fails_for_span_outside_concept_range() -> None:
    outside_span = _span(char_start=0, char_end=9999)
    item = _item(spans=[outside_span])
    result = SourceFaithfulnessValidator().validate(_payload(item=item))
    assert result.passed is False
    assert result.evidence is not None
    assert outside_span in result.evidence


def test_faithfulness_fails_when_concept_not_found() -> None:
    item = _item(concept_id="unknown-concept")
    result = SourceFaithfulnessValidator().validate(_payload(item=item))
    assert result.passed is False
    assert "unknown-concept" in (result.reason or "")


def test_faithfulness_passes_when_span_within_any_concept_span() -> None:
    item_span = _span(char_start=600, char_end=700)
    concept = _concept(
        spans=[_span(char_start=0, char_end=500), _span(char_start=500, char_end=800)]
    )
    item = _item(spans=[item_span])
    result = SourceFaithfulnessValidator().validate(_payload(item=item, graph=_graph([concept])))
    assert result.passed is True


def test_faithfulness_collects_all_bad_spans() -> None:
    bad1 = _span(char_start=0, char_end=9999)
    bad2 = _span(doc_id="other-doc", char_start=0, char_end=100)
    item = _item(spans=[bad1, bad2])
    result = SourceFaithfulnessValidator().validate(_payload(item=item))
    assert result.passed is False
    assert result.evidence is not None
    assert len(result.evidence) == 2


# ---------------------------------------------------------------------------
# ClarityValidator
# ---------------------------------------------------------------------------


def test_clarity_passes_for_valid_concept() -> None:
    result = ClarityValidator().validate(_payload())
    assert result.passed is True


def test_clarity_fails_for_unknown_concept_id() -> None:
    item = _item(concept_id="no-such-concept")
    result = ClarityValidator().validate(_payload(item=item))
    assert result.passed is False
    assert "no-such-concept" in (result.reason or "")


def test_clarity_fails_for_empty_learning_objective() -> None:
    concept = _concept(learning_objective="   ")
    item = _item(concept_id=concept.id)
    result = ClarityValidator().validate(
        _payload(item=item, graph=_graph([concept]))
    )
    assert result.passed is False
    assert "learning_objective" in (result.reason or "")


def test_clarity_passes_for_non_empty_learning_objective() -> None:
    concept = _concept(learning_objective="Explain photosynthesis.")
    item = _item(concept_id=concept.id)
    result = ClarityValidator().validate(_payload(item=item, graph=_graph([concept])))
    assert result.passed is True
