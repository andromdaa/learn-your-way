"""Unit tests for ExampleReplacer — all model and validator calls are mocked."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from syrupy.assertion import SnapshotAssertion

from lesson_graph.models import ConceptNode, LessonGraph, SourceSpan
from lyw_core.personalization.replace import ExampleReplacer
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
    return ConceptNode(
        id="c1",
        title="Photosynthesis",
        summary=(
            "Photosynthesis is like a tiny factory inside a leaf. "
            "Imagine a green machine that turns sunlight into food."
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
