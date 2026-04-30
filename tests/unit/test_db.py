"""Unit tests for the SQLite DAO layer.

All tests use an in-memory SQLite database — no filesystem, no services.
"""

import sqlite3

import pytest

from lesson_graph import AssessmentItem, ConceptNode, LessonGraph, SourceSpan
from lyw_core.db import Database


def _span(
    doc_id: str = "doc-1", char_start: int = 0, char_end: int = 100
) -> SourceSpan:
    return SourceSpan(
        doc_id=doc_id,
        page_start=1,
        page_end=2,
        char_start=char_start,
        char_end=char_end,
    )


def _concept(id: str = "c1", spans: list[SourceSpan] | None = None) -> ConceptNode:
    return ConceptNode(
        id=id,
        title=f"Title {id}",
        summary=f"Summary for {id}.",
        learning_objective=f"Objective for {id}.",
        source_spans=spans or [_span()],
        prerequisites=[],
    )


def _graph(
    id: str = "g1",
    source_id: str = "src-1",
    concepts: list[ConceptNode] | None = None,
) -> LessonGraph:
    return LessonGraph(
        id=id,
        source_id=source_id,
        concepts=concepts or [_concept()],
    )


# ---------------------------------------------------------------------------
# Database initialisation
# ---------------------------------------------------------------------------


async def test_database_initialises() -> None:
    db = await Database.connect(":memory:")
    await db.close()


# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------


async def test_add_and_get_source() -> None:
    db = await Database.connect(":memory:")
    await db.add_source("doc-1", "/data/doc.pdf", "abc123")
    row = await db.get_source("doc-1")
    assert row is not None
    assert row["doc_id"] == "doc-1"
    assert row["path"] == "/data/doc.pdf"
    assert row["sha256"] == "abc123"
    await db.close()


async def test_get_source_missing_returns_none() -> None:
    db = await Database.connect(":memory:")
    row = await db.get_source("no-such-id")
    assert row is None
    await db.close()


async def test_add_source_duplicate_raises() -> None:
    db = await Database.connect(":memory:")
    await db.add_source("doc-1", "/data/doc.pdf", "abc123")
    with pytest.raises(sqlite3.IntegrityError):
        await db.add_source("doc-1", "/data/other.pdf", "def456")
    await db.close()


# ---------------------------------------------------------------------------
# LessonGraph round-trip
# ---------------------------------------------------------------------------


async def test_upsert_and_get_lesson_graph_round_trip() -> None:
    db = await Database.connect(":memory:")
    await db.add_source("src-1", "/data/src.pdf", "sha1")

    graph = _graph()
    await db.upsert_lesson_graph(graph)

    retrieved = await db.get_lesson_graph("g1")
    assert retrieved is not None
    assert retrieved == graph
    await db.close()


async def test_round_trip_multiple_concepts() -> None:
    db = await Database.connect(":memory:")
    await db.add_source("src-1", "/data/src.pdf", "sha1")

    concepts = [
        _concept("c1", [_span("doc-1", 0, 50), _span("doc-1", 100, 200)]),
        _concept("c2", [_span("doc-1", 200, 300)]),
        _concept("c3", [_span("doc-2", 0, 80)]),
    ]
    graph = _graph("g1", "src-1", concepts)
    await db.upsert_lesson_graph(graph)

    retrieved = await db.get_lesson_graph("g1")
    assert retrieved is not None
    assert len(retrieved.concepts) == 3
    assert retrieved == graph
    await db.close()


async def test_round_trip_preserves_prerequisites() -> None:
    db = await Database.connect(":memory:")
    await db.add_source("src-1", "/data/src.pdf", "sha1")

    c1 = _concept("c1")
    c2 = ConceptNode(
        id="c2",
        title="Advanced",
        summary="Builds on c1.",
        learning_objective="Apply c1 concepts.",
        source_spans=[_span()],
        prerequisites=["c1"],
    )
    graph = _graph("g1", "src-1", [c1, c2])
    await db.upsert_lesson_graph(graph)

    retrieved = await db.get_lesson_graph("g1")
    assert retrieved is not None
    c2_retrieved = next(c for c in retrieved.concepts if c.id == "c2")
    assert c2_retrieved.prerequisites == ["c1"]
    await db.close()


async def test_get_lesson_graph_missing_returns_none() -> None:
    db = await Database.connect(":memory:")
    result = await db.get_lesson_graph("no-such-id")
    assert result is None
    await db.close()


async def test_upsert_is_idempotent() -> None:
    db = await Database.connect(":memory:")
    await db.add_source("src-1", "/data/src.pdf", "sha1")

    graph = _graph()
    await db.upsert_lesson_graph(graph)
    await db.upsert_lesson_graph(graph)

    retrieved = await db.get_lesson_graph("g1")
    assert retrieved is not None
    assert retrieved == graph
    await db.close()


async def test_upsert_replaces_concepts_on_update() -> None:
    db = await Database.connect(":memory:")
    await db.add_source("src-1", "/data/src.pdf", "sha1")

    graph_v1 = _graph("g1", "src-1", [_concept("c1"), _concept("c2")])
    await db.upsert_lesson_graph(graph_v1)

    graph_v2 = _graph("g1", "src-1", [_concept("c3")])
    await db.upsert_lesson_graph(graph_v2)

    retrieved = await db.get_lesson_graph("g1")
    assert retrieved is not None
    assert len(retrieved.concepts) == 1
    assert retrieved.concepts[0].id == "c3"
    await db.close()


# ---------------------------------------------------------------------------
# Assessment item helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Attempt DAO tests
# ---------------------------------------------------------------------------


async def test_record_attempt_and_get_profile_attempts() -> None:
    """record_attempt stores a row; get_profile_attempts returns it."""
    db = await Database.connect(":memory:")
    await db.add_source("src-1", "/data/src.pdf", "sha1")
    concept = _concept("c1")
    graph = _graph("g1", "src-1", [concept])
    await db.upsert_lesson_graph(graph)

    # Need a profile before inserting an attempt (FK)
    from lyw_core.profiles.models import LearnerProfile

    profile = LearnerProfile(id="p1", grade_level="5", interests=[], goals=[])
    await db.add_profile(profile)

    # Need an assessment item (FK)
    item = _item("item-1", "c1")
    await db.add_assessment_item(item)

    await db.record_attempt("p1", "item-1", "my answer", correct=True)

    attempts = await db.get_profile_attempts("p1")
    assert len(attempts) == 1
    a = attempts[0]
    assert a.profile_id == "p1"
    assert a.item_id == "item-1"
    assert a.response == "my answer"
    assert a.correct is True
    assert a.attempted_at != ""
    await db.close()


async def test_get_profile_attempts_returns_only_own_profile() -> None:
    """get_profile_attempts filters by profile_id."""
    db = await Database.connect(":memory:")
    await db.add_source("src-1", "/data/src.pdf", "sha1")
    concept = _concept("c1")
    graph = _graph("g1", "src-1", [concept])
    await db.upsert_lesson_graph(graph)

    from lyw_core.profiles.models import LearnerProfile

    for pid in ("p1", "p2"):
        profile = LearnerProfile(id=pid, grade_level="5", interests=[], goals=[])
        await db.add_profile(profile)

    item = _item("item-1", "c1")
    await db.add_assessment_item(item)

    await db.record_attempt("p1", "item-1", "answer-p1", correct=True)
    await db.record_attempt("p2", "item-1", "answer-p2", correct=False)

    p1_attempts = await db.get_profile_attempts("p1")
    assert len(p1_attempts) == 1
    assert p1_attempts[0].profile_id == "p1"

    p2_attempts = await db.get_profile_attempts("p2")
    assert len(p2_attempts) == 1
    assert p2_attempts[0].profile_id == "p2"
    await db.close()


async def test_get_profile_attempts_empty_for_no_attempts() -> None:
    """get_profile_attempts returns empty list when profile has no attempts."""
    db = await Database.connect(":memory:")
    await db.add_source("src-1", "/data/src.pdf", "sha1")

    from lyw_core.profiles.models import LearnerProfile

    profile = LearnerProfile(id="p1", grade_level="5", interests=[], goals=[])
    await db.add_profile(profile)

    attempts = await db.get_profile_attempts("p1")
    assert attempts == []
    await db.close()


async def test_record_attempt_stores_correct_false() -> None:
    """record_attempt stores correct=False (INTEGER 0) and returns bool False."""
    db = await Database.connect(":memory:")
    await db.add_source("src-1", "/data/src.pdf", "sha1")
    concept = _concept("c1")
    graph = _graph("g1", "src-1", [concept])
    await db.upsert_lesson_graph(graph)

    from lyw_core.profiles.models import LearnerProfile

    profile = LearnerProfile(id="p1", grade_level="5", interests=[], goals=[])
    await db.add_profile(profile)

    item = _item("item-1", "c1")
    await db.add_assessment_item(item)

    await db.record_attempt("p1", "item-1", "wrong answer", correct=False)

    attempts = await db.get_profile_attempts("p1")
    assert len(attempts) == 1
    assert attempts[0].correct is False
    await db.close()


async def test_get_item_by_id_returns_assessment_item() -> None:
    """get_item_by_id fetches a single AssessmentItem by its id."""
    db = await Database.connect(":memory:")
    await db.add_source("src-1", "/data/src.pdf", "sha1")
    concept = _concept("c1")
    graph = _graph("g1", "src-1", [concept])
    await db.upsert_lesson_graph(graph)

    item = _item("item-1", "c1")
    await db.add_assessment_item(item)

    fetched = await db.get_item_by_id("item-1")
    assert fetched is not None
    assert fetched.id == "item-1"
    assert fetched.concept_id == "c1"


async def test_get_item_by_id_missing_returns_none() -> None:
    """get_item_by_id returns None for unknown id."""
    db = await Database.connect(":memory:")
    result = await db.get_item_by_id("no-such-item")
    assert result is None
    await db.close()
