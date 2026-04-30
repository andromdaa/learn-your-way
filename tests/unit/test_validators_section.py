"""Unit tests for section-quality validators (TDD-strict)."""

from __future__ import annotations

from lesson_graph.models import AssessmentItem, ConceptNode, SourceSpan
from lyw_core.validators.section_quality import (
    ActiveLearningValidator,
    CoverageValidator,
    EmphasisValidator,
    SectionQuizPayload,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _span() -> SourceSpan:
    return SourceSpan(
        doc_id="doc-1", page_start=1, page_end=2, char_start=0, char_end=100
    )


def _concept(cid: str, prerequisites: list[str] | None = None) -> ConceptNode:
    return ConceptNode(
        id=cid,
        title=f"Concept {cid}",
        summary=f"Summary for {cid}.",
        learning_objective=f"Understand {cid}.",
        source_spans=[_span()],
        prerequisites=prerequisites or [],
    )


def _item(
    iid: str,
    concept_id: str,
    bloom_level: str | None = "remember",
) -> AssessmentItem:
    return AssessmentItem(
        id=iid,
        kind="mcq",
        prompt=f"Question {iid}",
        rationale="Rationale.",
        source_spans=[_span()],
        difficulty="easy",
        concept_id=concept_id,
        bloom_level=bloom_level,
    )


# ---------------------------------------------------------------------------
# CoverageValidator
# ---------------------------------------------------------------------------


def test_coverage_passes_when_all_concepts_have_items() -> None:
    concepts = [_concept("c1"), _concept("c2")]
    items = [_item("i1", "c1"), _item("i2", "c2")]
    result = CoverageValidator().validate(SectionQuizPayload(concepts, items))
    assert result.passed is True


def test_coverage_passes_with_multiple_items_per_concept() -> None:
    concepts = [_concept("c1")]
    items = [_item("i1", "c1"), _item("i2", "c1")]
    result = CoverageValidator().validate(SectionQuizPayload(concepts, items))
    assert result.passed is True


def test_coverage_fails_when_concept_has_no_items() -> None:
    concepts = [_concept("c1"), _concept("c2")]
    items = [_item("i1", "c1")]  # c2 uncovered
    result = CoverageValidator().validate(SectionQuizPayload(concepts, items))
    assert result.passed is False
    assert result.reason is not None
    assert "c2" in result.reason


def test_coverage_fails_lists_all_uncovered_concepts() -> None:
    concepts = [_concept("c1"), _concept("c2"), _concept("c3")]
    items: list[AssessmentItem] = []
    result = CoverageValidator().validate(SectionQuizPayload(concepts, items))
    assert result.passed is False
    reason = result.reason or ""
    assert "c1" in reason
    assert "c2" in reason
    assert "c3" in reason


def test_coverage_passes_with_empty_concepts() -> None:
    result = CoverageValidator().validate(SectionQuizPayload([], []))
    assert result.passed is True


# ---------------------------------------------------------------------------
# EmphasisValidator
# ---------------------------------------------------------------------------


def test_emphasis_passes_when_high_prereq_has_items() -> None:
    # c1 has 2 prereqs and has items; c2 has 0 prereqs and has ≥2 items — but c1 is covered
    concepts = [_concept("c1", ["p1", "p2"]), _concept("c2", [])]
    items = [_item("i1", "c1"), _item("i2", "c2"), _item("i3", "c2")]
    result = EmphasisValidator().validate(SectionQuizPayload(concepts, items))
    assert result.passed is True


def test_emphasis_passes_when_no_zero_prereq_has_enough_items() -> None:
    # c1 has 2 prereqs and 0 items; c2 has 0 prereqs but only 1 item — threshold not met
    concepts = [_concept("c1", ["p1", "p2"]), _concept("c2", [])]
    items = [_item("i1", "c2")]  # c2 has only 1 item (< 2)
    result = EmphasisValidator().validate(SectionQuizPayload(concepts, items))
    assert result.passed is True


def test_emphasis_fails_when_high_prereq_zero_while_zero_prereq_has_two() -> None:
    concepts = [_concept("c1", ["p1", "p2"]), _concept("c2", [])]
    items = [_item("i1", "c2"), _item("i2", "c2")]  # c2 has 2; c1 (high prereq) has 0
    result = EmphasisValidator().validate(SectionQuizPayload(concepts, items))
    assert result.passed is False
    assert result.reason is not None
    assert "c1" in result.reason


def test_emphasis_passes_with_no_high_prereq_concepts() -> None:
    concepts = [_concept("c1", []), _concept("c2", ["p1"])]
    items = [_item("i1", "c2"), _item("i2", "c2")]
    result = EmphasisValidator().validate(SectionQuizPayload(concepts, items))
    assert result.passed is True


def test_emphasis_passes_with_empty_section() -> None:
    result = EmphasisValidator().validate(SectionQuizPayload([], []))
    assert result.passed is True


# ---------------------------------------------------------------------------
# ActiveLearningValidator
# ---------------------------------------------------------------------------


def test_active_learning_passes_with_apply_item() -> None:
    concepts = [_concept("c1")]
    items = [_item("i1", "c1", bloom_level="apply")]
    result = ActiveLearningValidator().validate(SectionQuizPayload(concepts, items))
    assert result.passed is True


def test_active_learning_passes_with_analyze_item() -> None:
    result = ActiveLearningValidator().validate(
        SectionQuizPayload([_concept("c1")], [_item("i1", "c1", "analyze")])
    )
    assert result.passed is True


def test_active_learning_passes_with_evaluate_item() -> None:
    result = ActiveLearningValidator().validate(
        SectionQuizPayload([_concept("c1")], [_item("i1", "c1", "evaluate")])
    )
    assert result.passed is True


def test_active_learning_passes_with_create_item() -> None:
    result = ActiveLearningValidator().validate(
        SectionQuizPayload([_concept("c1")], [_item("i1", "c1", "create")])
    )
    assert result.passed is True


def test_active_learning_fails_when_all_remember() -> None:
    concepts = [_concept("c1")]
    items = [_item("i1", "c1", "remember"), _item("i2", "c1", "understand")]
    result = ActiveLearningValidator().validate(SectionQuizPayload(concepts, items))
    assert result.passed is False


def test_active_learning_fails_when_all_none_bloom() -> None:
    concepts = [_concept("c1")]
    items = [_item("i1", "c1", None), _item("i2", "c1", None)]
    result = ActiveLearningValidator().validate(SectionQuizPayload(concepts, items))
    assert result.passed is False


def test_active_learning_treats_none_as_remember() -> None:
    # One None (treated as remember), one apply — should pass
    concepts = [_concept("c1")]
    items = [_item("i1", "c1", None), _item("i2", "c1", "apply")]
    result = ActiveLearningValidator().validate(SectionQuizPayload(concepts, items))
    assert result.passed is True


def test_active_learning_fails_with_empty_items() -> None:
    result = ActiveLearningValidator().validate(
        SectionQuizPayload([_concept("c1")], [])
    )
    assert result.passed is False
