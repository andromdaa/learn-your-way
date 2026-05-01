"""Unit tests for MnemonicGenerator — model and validator calls mocked."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lesson_graph.models import ConceptNode, LessonGraph, SourceSpan
from lyw_core.assessment.mnemonic import MnemonicGenerator
from lyw_core.validators.base import ValidationError, ValidationResult


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
            "Photosynthesis is the process by which green plants use sunlight, "
            "water, and carbon dioxide to produce glucose and oxygen."
        ),
        learning_objective="Explain how plants convert light into chemical energy.",
        source_spans=[_span()],
    )


def _graph(concept: ConceptNode | None = None) -> LessonGraph:
    return LessonGraph(id="g1", source_id="doc-1", concepts=[concept or _concept()])


# ---------------------------------------------------------------------------
# Faithfulness gate raises ValidationError on failure
# ---------------------------------------------------------------------------


async def test_mnemonic_raises_on_faithfulness_failure() -> None:
    model = AsyncMock()
    model.complete = AsyncMock(return_value="Some mnemonic text")

    validator = MagicMock()
    validator.validate = MagicMock(
        return_value=ValidationResult(passed=False, reason="span out of range")
    )

    gen = MnemonicGenerator(model_client=model, faithfulness_validator=validator)
    concept = _concept()
    with pytest.raises(ValidationError) as exc_info:
        await gen.generate(concept, _graph(concept))

    assert "span out of range" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Model is called with concept content
# ---------------------------------------------------------------------------


async def test_mnemonic_calls_model_with_concept_content() -> None:
    model = AsyncMock()
    model.complete = AsyncMock(return_value="PWGCO mnemonic")

    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(passed=True))

    gen = MnemonicGenerator(model_client=model, faithfulness_validator=validator)
    concept = _concept()
    await gen.generate(concept, _graph(concept))

    call_args = model.complete.call_args
    messages = call_args[0][0]
    combined = " ".join(m["content"] for m in messages)
    assert "Photosynthesis" in combined


# ---------------------------------------------------------------------------
# Faithfulness validator called exactly once
# ---------------------------------------------------------------------------


async def test_mnemonic_calls_faithfulness_validator_once() -> None:
    model = AsyncMock()
    model.complete = AsyncMock(return_value="mnemonic text")

    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(passed=True))

    gen = MnemonicGenerator(model_client=model, faithfulness_validator=validator)
    concept = _concept()
    await gen.generate(concept, _graph(concept))

    validator.validate.assert_called_once()
