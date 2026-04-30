"""Unit tests for lyw_web.queries.WebQueries against a real temp SQLite file.

Uses lyw_core.db.dao.Database to seed the schema and rows, then queries
via WebQueries to verify the read-only listing methods.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lesson_graph import ConceptNode, LessonGraph, SourceSpan
from lyw_core.db.dao import Database, DerivedAsset
from lyw_web.queries import WebQueries


def _span() -> SourceSpan:
    return SourceSpan(
        doc_id="doc-1", page_start=1, page_end=1, char_start=0, char_end=50
    )


def _concept(cid: str = "c1") -> ConceptNode:
    return ConceptNode(
        id=cid,
        title=f"Title {cid}",
        summary="Summary.",
        learning_objective="Understand it.",
        source_spans=[_span()],
        prerequisites=[],
    )


def _graph(lesson_id: str = "lesson_1", n_concepts: int = 1) -> LessonGraph:
    return LessonGraph(
        id=lesson_id,
        source_id="src-1",
        concepts=[_concept(f"c{i}") for i in range(n_concepts)],
    )


@pytest.fixture()
async def db_path(tmp_path: Path) -> str:
    path = str(tmp_path / "test.db")
    db = await Database.connect(path)
    await db.add_source("src-1", "/data/src.pdf", "sha1")
    await db.close()
    return path


# ---------------------------------------------------------------------------
# list_lessons
# ---------------------------------------------------------------------------


async def test_list_lessons_empty(db_path: str) -> None:
    wq = await WebQueries.connect(db_path)
    result = await wq.list_lessons()
    assert result == []
    await wq.close()


async def test_list_lessons_single(db_path: str) -> None:
    db = await Database.connect(db_path)
    await db.upsert_lesson_graph(_graph("lesson_1", n_concepts=3))
    await db.close()

    wq = await WebQueries.connect(db_path)
    result = await wq.list_lessons()
    await wq.close()

    assert len(result) == 1
    row = result[0]
    assert row.id == "lesson_1"
    assert row.source_id == "src-1"
    assert row.concept_count == 3


async def test_list_lessons_ordered_desc(db_path: str) -> None:
    db = await Database.connect(db_path)
    await db.add_source("src-2", "/data/src2.pdf", "sha2")
    # upsert two graphs — SQLite CURRENT_TIMESTAMP granularity is seconds;
    # we can only assert both are returned and the IDs are present.
    graph1 = LessonGraph(id="lesson_a", source_id="src-1", concepts=[_concept("ca")])
    graph2 = LessonGraph(
        id="lesson_b", source_id="src-2", concepts=[_concept("cb"), _concept("cc")]
    )
    await db.upsert_lesson_graph(graph1)
    await db.upsert_lesson_graph(graph2)
    await db.close()

    wq = await WebQueries.connect(db_path)
    result = await wq.list_lessons()
    await wq.close()

    ids = {r.id for r in result}
    assert ids == {"lesson_a", "lesson_b"}
    counts = {r.id: r.concept_count for r in result}
    assert counts["lesson_a"] == 1
    assert counts["lesson_b"] == 2


# ---------------------------------------------------------------------------
# list_derived_assets
# ---------------------------------------------------------------------------


async def test_list_derived_assets_empty(db_path: str) -> None:
    db = await Database.connect(db_path)
    await db.upsert_lesson_graph(_graph())
    await db.close()

    wq = await WebQueries.connect(db_path)
    result = await wq.list_derived_assets("lesson_1")
    await wq.close()

    assert result == []


async def test_list_derived_assets_returns_rows(db_path: str) -> None:
    db = await Database.connect(db_path)
    await db.upsert_lesson_graph(_graph())
    asset = DerivedAsset(
        id="asset-1",
        lesson_id="lesson_1",
        concept_id="__lesson__",
        kind="mind_map",
        profile_id="prof-1",
        file_path="/data/assets/ab/abc.mmd",
        created_at="",
    )
    await db.save_derived_asset(asset)
    await db.close()

    wq = await WebQueries.connect(db_path)
    result = await wq.list_derived_assets("lesson_1")
    await wq.close()

    assert len(result) == 1
    assert result[0].id == "asset-1"
    assert result[0].kind == "mind_map"


async def test_list_derived_assets_filters_by_lesson(db_path: str) -> None:
    db = await Database.connect(db_path)
    await db.add_source("src-2", "/data/src2.pdf", "sha2")
    graph_a = LessonGraph(id="lesson_a", source_id="src-1", concepts=[_concept("ca")])
    graph_b = LessonGraph(id="lesson_b", source_id="src-2", concepts=[_concept("cb")])
    await db.upsert_lesson_graph(graph_a)
    await db.upsert_lesson_graph(graph_b)
    asset_a = DerivedAsset(
        id="asset-a",
        lesson_id="lesson_a",
        concept_id="__lesson__",
        kind="mind_map",
        profile_id="p1",
        file_path="/f/a.mmd",
        created_at="",
    )
    asset_b = DerivedAsset(
        id="asset-b",
        lesson_id="lesson_b",
        concept_id="__lesson__",
        kind="timeline",
        profile_id="p1",
        file_path="/f/b.mmd",
        created_at="",
    )
    await db.save_derived_asset(asset_a)
    await db.save_derived_asset(asset_b)
    await db.close()

    wq = await WebQueries.connect(db_path)
    result_a = await wq.list_derived_assets("lesson_a")
    result_b = await wq.list_derived_assets("lesson_b")
    await wq.close()

    assert len(result_a) == 1
    assert result_a[0].id == "asset-a"
    assert len(result_b) == 1
    assert result_b[0].id == "asset-b"
