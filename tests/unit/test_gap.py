"""TDD-strict tests for GapDetector.

Tests are written before the implementation. Each test names one branch of the
gap detection algorithm from the T12 task file.

Gap detection algorithm:
1. Load all attempts for the profile; filter to incorrect ones.
2. For the most recent incorrect attempt, look up the concept_id from
   assessment_items.
3. Retrieve the ConceptNode for that concept_id from the lesson graph.
4. Walk concept.prerequisites in list order (index 0 = highest priority) and
   return the first prerequisite concept_id for which the learner has no
   correct attempt.
5. If all prerequisites are mastered, or there are no prerequisites, or there
   are no incorrect attempts, return None.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock

import pytest

from lesson_graph import AssessmentItem, ConceptNode, LessonGraph, SourceSpan
from lyw_core.assessment.gap import GapDetector
from lyw_core.db.dao import AttemptRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _span() -> SourceSpan:
    return SourceSpan(doc_id="doc-1", page_start=1, page_end=2, char_start=0, char_end=100)


def _concept(id: str, prerequisites: list[str] | None = None) -> ConceptNode:
    return ConceptNode(
        id=id,
        title=f"Title {id}",
        summary=f"Summary {id}",
        learning_objective=f"Objective {id}",
        source_spans=[_span()],
        prerequisites=prerequisites or [],
    )


def _item(id: str, concept_id: str) -> AssessmentItem:
    return AssessmentItem(
        id=id,
        kind="mcq",
        prompt=f"Question for {concept_id}",
        rationale="Some rationale",
        source_spans=[_span()],
        difficulty="easy",
        concept_id=concept_id,
        correct_answer="A",
    )


def _attempt(
    id: str,
    item_id: str,
    profile_id: str = "p1",
    correct: bool = False,
    attempted_at: str = "2026-04-30T12:00:00Z",
) -> AttemptRecord:
    return AttemptRecord(
        id=id,
        profile_id=profile_id,
        item_id=item_id,
        response="some answer",
        correct=correct,
        attempted_at=attempted_at,
    )


def _make_dao(
    attempts: list[AttemptRecord],
    items_by_id: dict[str, AssessmentItem],
) -> Any:
    """Build an AsyncMock DAO with stubbed get_profile_attempts and
    get_item_by_id."""

    dao = AsyncMock()
    dao.get_profile_attempts = AsyncMock(return_value=attempts)

    async def _get_item(item_id: str) -> AssessmentItem | None:
        return items_by_id.get(item_id)

    dao.get_item_by_id = AsyncMock(side_effect=_get_item)
    return dao


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_smoke_failed_item_returns_unmastered_prerequisite() -> None:
    """Most basic path: one wrong answer → concept with prerequisite → prereq
    returned because learner has never answered it correctly."""
    prereq_concept = _concept("prereq-1")
    target_concept = _concept("target-1", prerequisites=["prereq-1"])
    graph = LessonGraph(
        id="g1", source_id="src-1", concepts=[prereq_concept, target_concept]
    )

    item = _item("item-1", "target-1")
    attempts = [_attempt("a1", "item-1", correct=False)]
    dao = _make_dao(attempts, {"item-1": item})

    detector = GapDetector()
    result = await detector.next_concept("p1", graph, dao)
    assert result is not None
    assert result.id == "prereq-1"


@pytest.mark.asyncio
async def test_all_prerequisites_mastered_returns_none() -> None:
    """Learner answered prereq correctly → no gap → return None."""
    prereq_concept = _concept("prereq-1")
    target_concept = _concept("target-1", prerequisites=["prereq-1"])
    graph = LessonGraph(
        id="g1", source_id="src-1", concepts=[prereq_concept, target_concept]
    )

    prereq_item = _item("prereq-item-1", "prereq-1")
    target_item = _item("item-1", "target-1")
    attempts = [
        _attempt("a1", "item-1", correct=False),
        _attempt("a2", "prereq-item-1", correct=True),
    ]
    dao = _make_dao(attempts, {"item-1": target_item, "prereq-item-1": prereq_item})

    detector = GapDetector()
    result = await detector.next_concept("p1", graph, dao)
    assert result is None


@pytest.mark.asyncio
async def test_no_attempts_returns_none() -> None:
    """Profile with no recorded attempts → no gap to detect → return None."""
    concept = _concept("c1", prerequisites=["prereq-1"])
    graph = LessonGraph(id="g1", source_id="src-1", concepts=[concept])

    dao = _make_dao([], {})

    detector = GapDetector()
    result = await detector.next_concept("p1", graph, dao)
    assert result is None


@pytest.mark.asyncio
async def test_no_incorrect_attempts_returns_none() -> None:
    """Profile with only correct attempts → no gap → return None."""
    target_concept = _concept("target-1", prerequisites=["prereq-1"])
    prereq_concept = _concept("prereq-1")
    graph = LessonGraph(
        id="g1", source_id="src-1", concepts=[prereq_concept, target_concept]
    )

    item = _item("item-1", "target-1")
    attempts = [_attempt("a1", "item-1", correct=True)]
    dao = _make_dao(attempts, {"item-1": item})

    detector = GapDetector()
    result = await detector.next_concept("p1", graph, dao)
    assert result is None


@pytest.mark.asyncio
async def test_multiple_failures_uses_most_recent() -> None:
    """Multiple incorrect attempts: gap detector uses the most recent one
    (latest attempted_at) to determine which concept to examine."""
    concept_a = _concept("concept-a", prerequisites=["prereq-a"])
    concept_b = _concept("concept-b", prerequisites=["prereq-b"])
    prereq_a = _concept("prereq-a")
    prereq_b = _concept("prereq-b")
    graph = LessonGraph(
        id="g1",
        source_id="src-1",
        concepts=[concept_a, concept_b, prereq_a, prereq_b],
    )

    item_a = _item("item-a", "concept-a")
    item_b = _item("item-b", "concept-b")

    attempts = [
        # Earlier failure on concept-a
        _attempt("a1", "item-a", correct=False, attempted_at="2026-04-30T10:00:00Z"),
        # Later failure on concept-b (most recent)
        _attempt("a2", "item-b", correct=False, attempted_at="2026-04-30T11:00:00Z"),
    ]
    dao = _make_dao(attempts, {"item-a": item_a, "item-b": item_b})

    detector = GapDetector()
    result = await detector.next_concept("p1", graph, dao)
    assert result is not None
    # Most recent failure is on concept-b → should return prereq-b
    assert result.id == "prereq-b"


@pytest.mark.asyncio
async def test_concept_with_no_prerequisites_returns_none() -> None:
    """Failed item on a concept with no prerequisites → return None (nothing to
    recommend as a prerequisite gap)."""
    concept = _concept("c1", prerequisites=[])
    graph = LessonGraph(id="g1", source_id="src-1", concepts=[concept])

    item = _item("item-1", "c1")
    attempts = [_attempt("a1", "item-1", correct=False)]
    dao = _make_dao(attempts, {"item-1": item})

    detector = GapDetector()
    result = await detector.next_concept("p1", graph, dao)
    assert result is None


@pytest.mark.asyncio
async def test_priority_order_first_unmastered_prerequisite_returned() -> None:
    """Prerequisites are walked in list order (index 0 = highest priority).
    The first unmastered prereq is returned, not any later one."""
    prereq_high = _concept("prereq-high")
    prereq_low = _concept("prereq-low")
    # Both are prerequisites; prereq-high is index 0 (highest priority)
    target = _concept("target-1", prerequisites=["prereq-high", "prereq-low"])
    graph = LessonGraph(
        id="g1",
        source_id="src-1",
        concepts=[prereq_high, prereq_low, target],
    )

    item = _item("item-1", "target-1")
    attempts = [_attempt("a1", "item-1", correct=False)]
    dao = _make_dao(attempts, {"item-1": item})

    detector = GapDetector()
    result = await detector.next_concept("p1", graph, dao)
    assert result is not None
    assert result.id == "prereq-high"


@pytest.mark.asyncio
async def test_first_prerequisite_mastered_returns_second() -> None:
    """If the highest-priority prereq is mastered, return the next unmastered
    one."""
    prereq_high = _concept("prereq-high")
    prereq_low = _concept("prereq-low")
    target = _concept("target-1", prerequisites=["prereq-high", "prereq-low"])
    graph = LessonGraph(
        id="g1",
        source_id="src-1",
        concepts=[prereq_high, prereq_low, target],
    )

    high_item = _item("high-item", "prereq-high")
    target_item = _item("item-1", "target-1")
    attempts = [
        _attempt("a1", "item-1", correct=False),
        # prereq-high is mastered
        _attempt("a2", "high-item", correct=True),
    ]
    dao = _make_dao(
        attempts, {"item-1": target_item, "high-item": high_item}
    )

    detector = GapDetector()
    result = await detector.next_concept("p1", graph, dao)
    assert result is not None
    assert result.id == "prereq-low"


@pytest.mark.asyncio
async def test_unknown_concept_id_in_item_returns_none() -> None:
    """If the item's concept_id doesn't exist in the lesson graph, return None
    gracefully rather than raising."""
    concept = _concept("known-concept")
    graph = LessonGraph(id="g1", source_id="src-1", concepts=[concept])

    # Item points to a concept not in the graph
    item = _item("item-1", "unknown-concept")
    attempts = [_attempt("a1", "item-1", correct=False)]
    dao = _make_dao(attempts, {"item-1": item})

    detector = GapDetector()
    result = await detector.next_concept("p1", graph, dao)
    assert result is None
