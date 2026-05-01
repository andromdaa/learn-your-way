"""Unit tests for the SQLite DAO layer.

All tests use an in-memory SQLite database — no filesystem, no services.
"""

import sqlite3

import pytest

from lesson_graph import ConceptNode, LessonGraph, SourceSpan
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
# DAO resilience: get_lesson_graph skips invalid rows (issue #65)
# ---------------------------------------------------------------------------


async def _insert_concept_without_spans(
    db: Database, lesson_id: str, concept_id: str
) -> None:
    """Insert a concept row with no source_spans to simulate a legacy bad row."""
    await db._conn.execute(
        """
        INSERT INTO concepts
            (id, lesson_id, title, summary, learning_objective, prerequisites)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (concept_id, lesson_id, "Bad Concept", "Bad summary", "Bad obj", "[]"),
    )
    await db._conn.commit()
    # Deliberately insert NO rows into source_spans for this concept.


async def test_get_lesson_graph_skips_concept_with_no_source_spans() -> None:
    """get_lesson_graph skips concepts whose stored rows have no source spans.

    This guards the DAO against legacy data that violated the source-fidelity
    invariant (issue #65).  One bad row must not prevent the rest of the lesson
    from loading.
    """
    db = await Database.connect(":memory:")
    await db.add_source("src-1", "/data/src.pdf", "sha1")

    # Insert the lesson row directly (bypass upsert to avoid schema validation)
    await db._conn.execute(
        "INSERT INTO lessons (id, source_id) VALUES (?, ?)",
        ("g1", "src-1"),
    )
    await db._conn.commit()

    # Good concept with a span
    good = _concept("c_good", [_span()])
    await db._conn.execute(
        """
        INSERT INTO concepts
            (id, lesson_id, title, summary, learning_objective, prerequisites)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            good.id,
            "g1",
            good.title,
            good.summary,
            good.learning_objective,
            "[]",
        ),
    )
    await db._conn.commit()
    for span in good.source_spans:
        await db._conn.execute(
            """
            INSERT INTO source_spans
                (concept_id, doc_id, page_start, page_end, char_start, char_end)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                good.id,
                span.doc_id,
                span.page_start,
                span.page_end,
                span.char_start,
                span.char_end,
            ),
        )
    await db._conn.commit()

    # Bad concept with no spans
    await _insert_concept_without_spans(db, "g1", "c_bad")

    retrieved = await db.get_lesson_graph("g1")
    assert retrieved is not None
    # Only the valid concept is returned; the bad one is silently skipped
    assert len(retrieved.concepts) == 1
    assert retrieved.concepts[0].id == good.id
    await db.close()


async def test_get_lesson_graph_all_bad_returns_empty_concepts() -> None:
    """get_lesson_graph returns a graph with no concepts when all rows are invalid."""
    db = await Database.connect(":memory:")
    await db.add_source("src-1", "/data/src.pdf", "sha1")

    await db._conn.execute(
        "INSERT INTO lessons (id, source_id) VALUES (?, ?)",
        ("g1", "src-1"),
    )
    await db._conn.commit()

    await _insert_concept_without_spans(db, "g1", "c_bad1")
    await _insert_concept_without_spans(db, "g1", "c_bad2")

    retrieved = await db.get_lesson_graph("g1")
    assert retrieved is not None
    assert retrieved.concepts == []
    await db.close()
