"""Unit tests for ReLeveler — all model and validator calls are mocked."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from lesson_graph.models import ConceptNode, LessonGraph, SourceSpan
from lyw_core.personalization.relevel import ReLeveler
from lyw_core.profiles.models import LearnerProfile
from lyw_core.validators.base import ValidationError, ValidationResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _span(char_start: int = 0, char_end: int = 500) -> SourceSpan:
    return SourceSpan(
        doc_id="doc-1",
        page_start=1,
        page_end=2,
        char_start=char_start,
        char_end=char_end,
    )


def _concept() -> ConceptNode:
    return ConceptNode(
        id="c1",
        title="Photosynthesis",
        summary="Photosynthesis is a process by which plants use sunlight, water, and CO2 to produce oxygen and energy in the form of glucose.",
        learning_objective="Explain how plants convert light into chemical energy.",
        source_spans=[_span()],
    )


def _profile(grade_level: str = "6") -> LearnerProfile:
    return LearnerProfile(
        id="p1",
        grade_level=grade_level,
        interests=["nature"],
        goals=["understand biology"],
    )


def _graph(concept: ConceptNode | None = None) -> LessonGraph:
    return LessonGraph(id="g1", source_id="doc-1", concepts=[concept or _concept()])


def _make_relevel(model_text: str = "Plants make food from sunlight.") -> ReLeveler:
    model = AsyncMock()
    model.complete = AsyncMock(return_value=model_text)

    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(passed=True))

    return ReLeveler(model_client=model, faithfulness_validator=validator)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_relevel_returns_text_and_profile() -> None:
    relev = _make_relevel("Plants make food from sunlight.")
    concept = _concept()
    text, profile = await relev.relevel(concept, _profile(), _graph(concept))

    assert text == "Plants make food from sunlight."
    assert profile.grade_level == "6"
    assert len(profile.replacements) == 1


async def test_relevel_replacement_record_fields() -> None:
    relev = _make_relevel("Simple text.")
    concept = _concept()
    _, profile = await relev.relevel(concept, _profile(), _graph(concept))

    rec = profile.replacements[0]
    assert rec.replacement_text == "Simple text."
    assert rec.justification  # non-empty
    assert "6" in rec.justification  # grade level injected
    assert rec.original_span == concept.source_spans[0]


async def test_relevel_calls_model_with_grade_level() -> None:
    model = AsyncMock()
    model.complete = AsyncMock(return_value="Re-leveled text.")
    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(passed=True))

    relev = ReLeveler(model_client=model, faithfulness_validator=validator)
    concept = _concept()
    await relev.relevel(concept, _profile(grade_level="9"), _graph(concept))

    call_args = model.complete.call_args
    messages = call_args[0][0]
    combined = " ".join(m["content"] for m in messages)
    assert "9" in combined


async def test_relevel_propagates_validation_error() -> None:
    model = AsyncMock()
    model.complete = AsyncMock(return_value="Some text.")
    validator = MagicMock()
    validator.validate = MagicMock(
        return_value=ValidationResult(passed=False, reason="span out of range")
    )

    relev = ReLeveler(model_client=model, faithfulness_validator=validator)
    concept = _concept()
    with pytest.raises(ValidationError) as exc_info:
        await relev.relevel(concept, _profile(), _graph(concept))
    assert "span out of range" in exc_info.value.reasons
