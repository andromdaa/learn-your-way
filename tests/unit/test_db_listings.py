"""Unit tests for the new DAO listing and delete methods.

All tests use in-memory SQLite — no filesystem, no external services.
"""

from __future__ import annotations

from lesson_graph import AssessmentItem, ConceptNode, LessonGraph, SourceSpan
from lyw_core.db import Database
from lyw_core.db.dao import DerivedAsset
from lyw_core.profiles.models import LearnerProfile


def _span(doc_id: str = "doc-1") -> SourceSpan:
    return SourceSpan(
        doc_id=doc_id, page_start=1, page_end=1, char_start=0, char_end=50
    )


def _concept(cid: str = "c1") -> ConceptNode:
    return ConceptNode(
        id=cid,
        title=f"Title {cid}",
        summary=f"Summary {cid}.",
        learning_objective=f"Objective {cid}.",
        source_spans=[_span()],
        prerequisites=[],
    )


def _graph(
    gid: str = "g1",
    source_id: str = "src-1",
    concepts: list[ConceptNode] | None = None,
) -> LessonGraph:
    return LessonGraph(id=gid, source_id=source_id, concepts=concepts or [_concept()])


def _item(item_id: str, concept_id: str, quiz_id: str | None = None) -> AssessmentItem:
    return AssessmentItem(
        id=item_id,
        kind="mcq",
        prompt=f"Q for {concept_id}",
        rationale="Rationale",
        source_spans=[_span()],
        difficulty="easy",
        concept_id=concept_id,
        correct_answer="A",
        quiz_id=quiz_id,
    )


# ---------------------------------------------------------------------------
# list_sources / get_source_row
# ---------------------------------------------------------------------------


async def test_list_sources_empty() -> None:
    db = await Database.connect(":memory:")
    assert await db.list_sources() == []
    await db.close()


async def test_list_sources_returns_source_without_lesson() -> None:
    db = await Database.connect(":memory:")
    await db.add_source("doc-1", "/data/doc.pdf", "abc123")
    rows = await db.list_sources()
    assert len(rows) == 1
    assert rows[0].doc_id == "doc-1"
    assert rows[0].sha256 == "abc123"
    assert rows[0].lesson_id is None
    await db.close()


async def test_list_sources_returns_lesson_id_when_ingested() -> None:
    db = await Database.connect(":memory:")
    await db.add_source("doc-1", "/data/doc.pdf", "abc")
    await db.upsert_lesson_graph(_graph("lesson_doc-1", "doc-1"))
    rows = await db.list_sources()
    assert rows[0].lesson_id == "lesson_doc-1"
    await db.close()


async def test_get_source_row_found() -> None:
    db = await Database.connect(":memory:")
    await db.add_source("doc-1", "/data/doc.pdf", "sha-abc")
    row = await db.get_source_row("doc-1")
    assert row is not None
    assert row.doc_id == "doc-1"
    assert row.path == "/data/doc.pdf"
    assert row.lesson_id is None
    await db.close()


async def test_get_source_row_missing_returns_none() -> None:
    db = await Database.connect(":memory:")
    assert await db.get_source_row("no-such-id") is None
    await db.close()


async def test_get_source_row_includes_lesson_id() -> None:
    db = await Database.connect(":memory:")
    await db.add_source("doc-1", "/data/doc.pdf", "sha")
    await db.upsert_lesson_graph(_graph("lesson_doc-1", "doc-1"))
    row = await db.get_source_row("doc-1")
    assert row is not None
    assert row.lesson_id == "lesson_doc-1"
    await db.close()


# ---------------------------------------------------------------------------
# list_lessons
# ---------------------------------------------------------------------------


async def test_list_lessons_empty() -> None:
    db = await Database.connect(":memory:")
    assert await db.list_lessons() == []
    await db.close()


async def test_list_lessons_returns_summary_with_concept_count() -> None:
    db = await Database.connect(":memory:")
    await db.add_source("src-1", "/data/src.pdf", "sha1")
    await db.upsert_lesson_graph(
        _graph("g1", "src-1", [_concept("c1"), _concept("c2")])
    )
    lessons = await db.list_lessons()
    assert len(lessons) == 1
    assert lessons[0].id == "g1"
    assert lessons[0].source_id == "src-1"
    assert lessons[0].concept_count == 2
    await db.close()


async def test_list_lessons_returns_all_lessons() -> None:
    db = await Database.connect(":memory:")
    await db.add_source("src-1", "/data/src.pdf", "sha1")
    await db.add_source("src-2", "/data/src2.pdf", "sha2")
    await db.upsert_lesson_graph(_graph("g1", "src-1", [_concept("c-g1")]))
    await db.upsert_lesson_graph(_graph("g2", "src-2", [_concept("c-g2")]))
    lessons = await db.list_lessons()
    assert len(lessons) == 2
    assert {lesson.id for lesson in lessons} == {"g1", "g2"}
    await db.close()


# ---------------------------------------------------------------------------
# delete_profile
# ---------------------------------------------------------------------------


async def test_delete_profile_returns_true_and_removes_row() -> None:
    db = await Database.connect(":memory:")
    profile = LearnerProfile(id="p1", grade_level="8", interests=[], goals=[])
    await db.add_profile(profile)
    assert await db.delete_profile("p1") is True
    assert await db.get_profile("p1") is None
    await db.close()


async def test_delete_profile_missing_returns_false() -> None:
    db = await Database.connect(":memory:")
    assert await db.delete_profile("no-such-profile") is False
    await db.close()


# ---------------------------------------------------------------------------
# list_derived_assets
# ---------------------------------------------------------------------------


async def test_list_derived_assets_empty() -> None:
    db = await Database.connect(":memory:")
    assert await db.list_derived_assets("lesson-x") == []
    await db.close()


async def test_list_derived_assets_filtered_by_lesson() -> None:
    db = await Database.connect(":memory:")
    a1 = DerivedAsset(
        id="a1",
        lesson_id="l1",
        concept_id="c1",
        kind="mnemonic",
        profile_id="p1",
        file_path="/f",
        created_at="2026-01-01T00:00:00Z",
    )
    a2 = DerivedAsset(
        id="a2",
        lesson_id="l2",
        concept_id="c1",
        kind="mnemonic",
        profile_id="p1",
        file_path="/f",
        created_at="2026-01-01T00:00:00Z",
    )
    await db.save_derived_asset(a1)
    await db.save_derived_asset(a2)
    rows = await db.list_derived_assets("l1")
    assert len(rows) == 1
    assert rows[0].id == "a1"
    await db.close()


async def test_list_derived_assets_filtered_by_kind() -> None:
    db = await Database.connect(":memory:")
    await db.save_derived_asset(
        DerivedAsset(
            id="a1",
            lesson_id="l1",
            concept_id="c1",
            kind="mnemonic",
            profile_id="p1",
            file_path="/f",
            created_at="2026-01-01T00:00:00Z",
        )
    )
    await db.save_derived_asset(
        DerivedAsset(
            id="a2",
            lesson_id="l1",
            concept_id="__lesson__",
            kind="mind_map",
            profile_id="p1",
            file_path="/f",
            created_at="2026-01-01T00:00:00Z",
        )
    )
    rows = await db.list_derived_assets("l1", kind="mnemonic")
    assert len(rows) == 1
    assert rows[0].id == "a1"
    await db.close()


async def test_list_derived_assets_filtered_by_profile() -> None:
    db = await Database.connect(":memory:")
    await db.save_derived_asset(
        DerivedAsset(
            id="a1",
            lesson_id="l1",
            concept_id="c1",
            kind="mnemonic",
            profile_id="p1",
            file_path="/f",
            created_at="2026-01-01T00:00:00Z",
        )
    )
    await db.save_derived_asset(
        DerivedAsset(
            id="a2",
            lesson_id="l1",
            concept_id="c1",
            kind="mnemonic",
            profile_id="p2",
            file_path="/f",
            created_at="2026-01-01T00:00:00Z",
        )
    )
    rows = await db.list_derived_assets("l1", profile_id="p1")
    assert len(rows) == 1
    assert rows[0].profile_id == "p1"
    await db.close()


# ---------------------------------------------------------------------------
# list_quizzes
# ---------------------------------------------------------------------------


async def test_list_quizzes_empty() -> None:
    db = await Database.connect(":memory:")
    await db.add_source("src-1", "/data/src.pdf", "sha1")
    await db.upsert_lesson_graph(_graph("g1", "src-1"))
    quizzes = await db.list_quizzes("g1")
    assert quizzes == []
    await db.close()


async def test_list_quizzes_returns_quiz_with_item_count() -> None:
    db = await Database.connect(":memory:")
    await db.add_source("src-1", "/data/src.pdf", "sha1")
    await db.upsert_lesson_graph(
        _graph("g1", "src-1", [_concept("c1"), _concept("c2")])
    )

    await db.add_assessment_item(_item("i1", "c1", quiz_id="quiz-1"))
    await db.add_assessment_item(_item("i2", "c2", quiz_id="quiz-1"))

    quizzes = await db.list_quizzes("g1")
    assert len(quizzes) == 1
    assert quizzes[0].quiz_id == "quiz-1"
    assert quizzes[0].item_count == 2
    await db.close()


async def test_list_quizzes_excludes_items_without_quiz_id() -> None:
    db = await Database.connect(":memory:")
    await db.add_source("src-1", "/data/src.pdf", "sha1")
    await db.upsert_lesson_graph(_graph("g1", "src-1", [_concept("c1")]))
    await db.add_assessment_item(_item("i1", "c1", quiz_id=None))
    quizzes = await db.list_quizzes("g1")
    assert quizzes == []
    await db.close()
