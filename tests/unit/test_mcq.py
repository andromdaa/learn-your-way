"""Unit tests for MCQGenerator — model and validator calls mocked.

DAO round-trip tests use an in-memory SQLite database. The concept row
is pre-inserted via add_source + upsert_lesson_graph so the FK on
assessment_items.concept_id is satisfied.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lesson_graph.models import AssessmentItem, ConceptNode, LessonGraph, SourceSpan
from lyw_core.assessment import MCQGenerator
from lyw_core.db import Database
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
            "Photosynthesis is the process by which green plants use sunlight, "
            "water, and carbon dioxide to make glucose and oxygen."
        ),
        learning_objective="Explain how plants convert light into chemical energy.",
        source_spans=[_span()],
    )


def _graph(concept: ConceptNode | None = None) -> LessonGraph:
    return LessonGraph(id="g1", source_id="doc-1", concepts=[concept or _concept()])


def _mcq(
    prompt: str = "What gas do plants release during photosynthesis?",
    options: list[str] | None = None,
    correct: str = "Oxygen",
    rationale: str = "Photosynthesis releases oxygen as a byproduct.",
    bloom: str = "understand",
    difficulty: str = "easy",
) -> dict[str, Any]:
    return {
        "prompt": prompt,
        "options": options or ["Oxygen", "Nitrogen", "Hydrogen", "Methane"],
        "correct_answer": correct,
        "rationale": rationale,
        "bloom_level": bloom,
        "difficulty": difficulty,
    }


def _passing_validator() -> MagicMock:
    v = MagicMock()
    v.validate = MagicMock(return_value=ValidationResult(passed=True))
    return v


async def _make_dao() -> Database:
    db = await Database.connect(":memory:")
    await db.add_source("doc-1", "/data/doc.pdf", "sha-1")
    await db.upsert_lesson_graph(_graph())
    return db


# ---------------------------------------------------------------------------
# Discard rules
# ---------------------------------------------------------------------------


async def test_mcq_discards_items_missing_correct_answer() -> None:
    bad: dict[str, Any] = _mcq()
    del bad["correct_answer"]
    model = AsyncMock()
    model.complete = AsyncMock(return_value=json.dumps([bad]))
    dao = await _make_dao()
    gen = MCQGenerator(model_client=model, validators=[_passing_validator()], dao=dao)
    items = await gen.generate(_concept(), _graph())
    assert items == []
    await dao.close()


async def test_mcq_discards_items_missing_bloom_level() -> None:
    bad: dict[str, Any] = _mcq()
    del bad["bloom_level"]
    model = AsyncMock()
    model.complete = AsyncMock(return_value=json.dumps([bad]))
    dao = await _make_dao()
    gen = MCQGenerator(model_client=model, validators=[_passing_validator()], dao=dao)
    items = await gen.generate(_concept(), _graph())
    assert items == []
    await dao.close()


async def test_mcq_discards_when_correct_answer_not_in_options() -> None:
    bad = _mcq(correct="NotAnOption")
    model = AsyncMock()
    model.complete = AsyncMock(return_value=json.dumps([bad]))
    dao = await _make_dao()
    gen = MCQGenerator(model_client=model, validators=[_passing_validator()], dao=dao)
    items = await gen.generate(_concept(), _graph())
    assert items == []
    await dao.close()


async def test_mcq_discards_when_not_four_options() -> None:
    bad = _mcq(options=["A", "B", "C"], correct="A")
    model = AsyncMock()
    model.complete = AsyncMock(return_value=json.dumps([bad]))
    dao = await _make_dao()
    gen = MCQGenerator(model_client=model, validators=[_passing_validator()], dao=dao)
    items = await gen.generate(_concept(), _graph())
    assert items == []
    await dao.close()


# ---------------------------------------------------------------------------
# Parse-failure paths
# ---------------------------------------------------------------------------


async def test_mcq_returns_empty_on_invalid_json() -> None:
    model = AsyncMock()
    model.complete = AsyncMock(return_value="not json")
    validator = _passing_validator()
    dao = await _make_dao()
    gen = MCQGenerator(model_client=model, validators=[validator], dao=dao)
    items = await gen.generate(_concept(), _graph())
    assert items == []
    validator.validate.assert_not_called()
    await dao.close()


async def test_mcq_returns_empty_on_empty_array() -> None:
    model = AsyncMock()
    model.complete = AsyncMock(return_value="[]")
    dao = await _make_dao()
    gen = MCQGenerator(model_client=model, validators=[_passing_validator()], dao=dao)
    items = await gen.generate(_concept(), _graph())
    assert items == []
    await dao.close()


# ---------------------------------------------------------------------------
# Discard-don't-raise on validator failure
# ---------------------------------------------------------------------------


async def test_mcq_does_not_raise_on_validator_failure() -> None:
    model = AsyncMock()
    model.complete = AsyncMock(return_value=json.dumps([_mcq()]))
    failing = MagicMock()
    failing.validate = MagicMock(
        return_value=ValidationResult(passed=False, reason="bad")
    )
    dao = await _make_dao()
    gen = MCQGenerator(model_client=model, validators=[failing], dao=dao)
    items = await gen.generate(_concept(), _graph())
    assert items == []
    await dao.close()


# ---------------------------------------------------------------------------
# DAO round-trip
# ---------------------------------------------------------------------------


async def test_mcq_persists_accepted_items() -> None:
    model = AsyncMock()
    model.complete = AsyncMock(return_value=json.dumps([_mcq()]))
    dao = await _make_dao()
    gen = MCQGenerator(model_client=model, validators=[_passing_validator()], dao=dao)
    items = await gen.generate(_concept(), _graph())
    assert len(items) == 1

    persisted = await dao.get_items_by_concept("c1")
    assert len(persisted) == 1
    assert persisted[0].id == items[0].id
    assert persisted[0].kind == "mcq"
    assert persisted[0].correct_answer == "Oxygen"
    assert persisted[0].bloom_level == "understand"
    assert persisted[0].difficulty == "easy"
    assert persisted[0].source_spans == items[0].source_spans
    await dao.close()


async def test_get_items_by_concept_empty_when_none_persisted() -> None:
    dao = await _make_dao()
    items = await dao.get_items_by_concept("c1")
    assert items == []
    await dao.close()


async def test_add_assessment_item_round_trip_preserves_optional_fields() -> None:
    dao = await _make_dao()
    item = AssessmentItem(
        id="manual-1",
        kind="short_answer",
        prompt="Describe photosynthesis.",
        rationale="Open response.",
        source_spans=[_span()],
        difficulty="medium",
        concept_id="c1",
        correct_answer=None,
        bloom_level=None,
    )
    await dao.add_assessment_item(item)
    retrieved = await dao.get_items_by_concept("c1")
    assert len(retrieved) == 1
    assert retrieved[0].correct_answer is None
    assert retrieved[0].bloom_level is None
    await dao.close()


async def test_add_assessment_item_fk_violation_when_concept_missing() -> None:
    dao = await Database.connect(":memory:")
    item = AssessmentItem(
        id="orphan-1",
        kind="mcq",
        prompt="?",
        rationale="?",
        source_spans=[_span()],
        difficulty="easy",
        concept_id="missing-concept",
    )
    with pytest.raises(sqlite3.IntegrityError):
        await dao.add_assessment_item(item)
    await dao.close()
