"""Unit tests for ExampleReplacer — all model and validator calls are mocked."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from syrupy.assertion import SnapshotAssertion

from lesson_graph.models import ConceptNode, LessonGraph, SourceSpan
from lyw_core.personalization.replace import ExampleReplacer, ReplaceSourceTooThinError
from lyw_core.profiles.models import LearnerProfile
from lyw_core.validators.base import ValidationResult


def _span(char_start: int = 0, char_end: int = 500) -> SourceSpan:
    return SourceSpan(
        doc_id="doc-1",
        page_start=1,
        page_end=2,
        char_start=char_start,
        char_end=char_end,
    )


def _concept() -> ConceptNode:
    # Summary is intentionally above the ReplaceSourceTooThinError thresholds
    # (>=200 chars, >=30 words AFTER stripping any leading title) so the
    # existing positive-path tests keep exercising the model + validator
    # rather than being short-circuited by the thin-source guard.
    return ConceptNode(
        id="c1",
        title="Photosynthesis",
        summary=(
            "Photosynthesis is like a tiny factory inside a leaf, where "
            "chloroplasts capture sunlight and use water and carbon dioxide "
            "from the air to build sugar molecules. Imagine a green machine "
            "that turns sunlight into food, releasing oxygen as a useful "
            "by-product for the rest of the living world to breathe."
        ),
        learning_objective="Explain how plants convert light into chemical energy.",
        source_spans=[_span()],
    )


def _profile() -> LearnerProfile:
    return LearnerProfile(
        id="p1",
        grade_level="6",
        interests=["soccer", "cooking"],
        goals=["understand biology"],
    )


def _graph(concept: ConceptNode | None = None) -> LessonGraph:
    return LessonGraph(id="g1", source_id="doc-1", concepts=[concept or _concept()])


_TWO_REPLACEMENTS_JSON = json.dumps(
    [
        {
            "original_text": "like a tiny factory inside a leaf",
            "replacement_text": "like a soccer team passing the ball down the field",
            "interest": "soccer",
        },
        {
            "original_text": "a green machine that turns sunlight into food",
            "replacement_text": "a chef in a green kitchen turning sunlight into a meal",
            "interest": "cooking",
        },
    ]
)


async def test_replace_returns_only_passing_records(
    snapshot: SnapshotAssertion,
) -> None:
    """Two replacements proposed; one fails faithfulness; only one returned."""
    model = AsyncMock()
    model.complete = AsyncMock(return_value=_TWO_REPLACEMENTS_JSON)

    validator = MagicMock()
    validator.validate = MagicMock(
        side_effect=[
            ValidationResult(passed=True),
            ValidationResult(passed=False, reason="span out of range"),
        ]
    )

    replacer = ExampleReplacer(model_client=model, faithfulness_validator=validator)
    concept = _concept()
    records = await replacer.replace(concept, _profile(), _graph(concept))

    assert len(records) == 1
    assert records[0].replacement_text.startswith("like a soccer team")
    assert "soccer" in records[0].justification
    assert records[0].original_span == concept.source_spans[0]
    assert snapshot == [r.model_dump() for r in records]


async def test_replace_returns_empty_on_invalid_json() -> None:
    model = AsyncMock()
    model.complete = AsyncMock(return_value="not a json string")
    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(passed=True))

    replacer = ExampleReplacer(model_client=model, faithfulness_validator=validator)
    concept = _concept()
    records = await replacer.replace(concept, _profile(), _graph(concept))

    assert records == []
    validator.validate.assert_not_called()


async def test_replace_returns_empty_on_empty_array() -> None:
    model = AsyncMock()
    model.complete = AsyncMock(return_value="[]")
    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(passed=True))

    replacer = ExampleReplacer(model_client=model, faithfulness_validator=validator)
    concept = _concept()
    records = await replacer.replace(concept, _profile(), _graph(concept))

    assert records == []


async def test_replace_skips_empty_replacement_text() -> None:
    payload = json.dumps(
        [
            {"original_text": "x", "replacement_text": "   ", "interest": "soccer"},
            {
                "original_text": "y",
                "replacement_text": "real replacement",
                "interest": "cooking",
            },
        ]
    )
    model = AsyncMock()
    model.complete = AsyncMock(return_value=payload)
    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(passed=True))

    replacer = ExampleReplacer(model_client=model, faithfulness_validator=validator)
    concept = _concept()
    records = await replacer.replace(concept, _profile(), _graph(concept))

    assert len(records) == 1
    assert records[0].replacement_text == "real replacement"


async def test_replace_does_not_raise_on_faithfulness_failure() -> None:
    """All replacements failing faithfulness => empty list, NO ValidationError."""
    model = AsyncMock()
    model.complete = AsyncMock(return_value=_TWO_REPLACEMENTS_JSON)
    validator = MagicMock()
    validator.validate = MagicMock(
        return_value=ValidationResult(passed=False, reason="bad span")
    )

    replacer = ExampleReplacer(model_client=model, faithfulness_validator=validator)
    concept = _concept()
    records = await replacer.replace(concept, _profile(), _graph(concept))

    assert records == []


async def test_replace_calls_model_with_interests() -> None:
    model = AsyncMock()
    model.complete = AsyncMock(return_value="[]")
    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(passed=True))

    replacer = ExampleReplacer(model_client=model, faithfulness_validator=validator)
    concept = _concept()
    await replacer.replace(concept, _profile(), _graph(concept))

    call_args = model.complete.call_args
    messages = call_args[0][0]
    combined = " ".join(m["content"] for m in messages)
    assert "soccer" in combined
    assert "cooking" in combined


async def test_replace_handles_json_fenced_response() -> None:
    """Model wrapping JSON in ```json ... ``` fences is parsed correctly."""
    fenced = f"```json\n{_TWO_REPLACEMENTS_JSON}\n```"
    model = AsyncMock()
    model.complete = AsyncMock(return_value=fenced)
    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(passed=True))

    replacer = ExampleReplacer(model_client=model, faithfulness_validator=validator)
    concept = _concept()
    records = await replacer.replace(concept, _profile(), _graph(concept))

    assert len(records) == 2


async def test_replace_handles_bare_fenced_response() -> None:
    """Model wrapping JSON in bare ``` ... ``` fences is parsed correctly."""
    fenced = f"```\n{_TWO_REPLACEMENTS_JSON}\n```"
    model = AsyncMock()
    model.complete = AsyncMock(return_value=fenced)
    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(passed=True))

    replacer = ExampleReplacer(model_client=model, faithfulness_validator=validator)
    concept = _concept()
    records = await replacer.replace(concept, _profile(), _graph(concept))

    assert len(records) == 2


async def test_replace_handles_json_uppercase_fenced_response() -> None:
    """Model wrapping JSON in ```JSON ... ``` fences (uppercase) is parsed correctly."""
    fenced = f"```JSON\n{_TWO_REPLACEMENTS_JSON}\n```"
    model = AsyncMock()
    model.complete = AsyncMock(return_value=fenced)
    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(passed=True))

    replacer = ExampleReplacer(model_client=model, faithfulness_validator=validator)
    concept = _concept()
    records = await replacer.replace(concept, _profile(), _graph(concept))

    assert len(records) == 2


# ---------------------------------------------------------------------------
# ReplaceSourceTooThinError guard (issue #77)
#
# When concept.summary lacks teachable content, the LLM has nothing meaningful
# to "replace" and would emit an interest-themed flourish unmoored from the
# source. The pre-flight guard raises before the model is called.
# ---------------------------------------------------------------------------


async def test_replace_raises_on_heading_only_summary() -> None:
    """Summary == title (chunker fallback) trips the guard; model NOT called."""
    model = AsyncMock()
    model.complete = AsyncMock(return_value=_TWO_REPLACEMENTS_JSON)
    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(passed=True))

    replacer = ExampleReplacer(model_client=model, faithfulness_validator=validator)
    concept = ConceptNode(
        id="c-heading-only",
        title="EQUATIONS AND INEQUALITIES",
        summary="EQUATIONS AND INEQUALITIES",
        learning_objective="Solve equations and inequalities.",
        source_spans=[_span()],
    )

    with pytest.raises(ReplaceSourceTooThinError) as excinfo:
        await replacer.replace(concept, _profile(), _graph(concept))

    assert excinfo.value.concept_id == "c-heading-only"
    assert excinfo.value.char_count == 0
    assert excinfo.value.word_count == 0
    model.complete.assert_not_called()
    validator.validate.assert_not_called()


async def test_replace_raises_when_summary_below_char_threshold() -> None:
    """Short summary (well under 200 chars) trips the guard."""
    model = AsyncMock()
    model.complete = AsyncMock(return_value=_TWO_REPLACEMENTS_JSON)
    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(passed=True))

    replacer = ExampleReplacer(model_client=model, faithfulness_validator=validator)
    concept = ConceptNode(
        id="c-short",
        title="Short Topic",
        summary="A brief sentence about plants and the sun.",
        learning_objective="Learn the basics.",
        source_spans=[_span()],
    )

    with pytest.raises(ReplaceSourceTooThinError) as excinfo:
        await replacer.replace(concept, _profile(), _graph(concept))

    assert excinfo.value.concept_id == "c-short"
    assert excinfo.value.char_count < 200
    model.complete.assert_not_called()


async def test_replace_raises_when_summary_below_word_threshold() -> None:
    """Body that meets char threshold via long words but has too few words trips the guard."""
    model = AsyncMock()
    model.complete = AsyncMock(return_value=_TWO_REPLACEMENTS_JSON)
    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(passed=True))

    replacer = ExampleReplacer(model_client=model, faithfulness_validator=validator)
    # 12 very long pseudo-words separated by single spaces. Char count is well
    # over 200 but word count is far below 30, so the word gate must trip.
    long_words = " ".join(["supercalifragilisticexpialidocious"] * 12)
    assert len(long_words) >= 200
    assert len(long_words.split()) < 30
    concept = ConceptNode(
        id="c-few-words",
        title="Topic",
        summary=long_words,
        learning_objective="Learn.",
        source_spans=[_span()],
    )

    with pytest.raises(ReplaceSourceTooThinError) as excinfo:
        await replacer.replace(concept, _profile(), _graph(concept))

    assert excinfo.value.concept_id == "c-few-words"
    assert excinfo.value.word_count < 30
    model.complete.assert_not_called()
