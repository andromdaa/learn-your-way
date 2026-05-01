"""Unit tests for worker/jobs/quiz.py — generate_quiz job."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from lesson_graph.models import ConceptNode, LessonGraph, SourceSpan


def _concept(cid: str = "c1") -> ConceptNode:
    return ConceptNode(
        id=cid,
        title="Test",
        summary="s",
        learning_objective="lo",
        source_spans=[SourceSpan(doc_id="d", page_start=1, page_end=1, char_start=0, char_end=10)],
    )


def _graph(concepts: list[ConceptNode] | None = None) -> LessonGraph:
    return LessonGraph(
        id="lesson-1",
        source_id="doc-1",
        concepts=concepts or [_concept()],
    )


def _item(item_id: str = "item-1") -> MagicMock:
    item = MagicMock()
    item.id = item_id
    return item


def _make_ctx(db: AsyncMock | None = None) -> dict[str, Any]:
    return {
        "db": db or AsyncMock(),
        "model_client": MagicMock(),
        "progress_factory": None,
    }


# ---------------------------------------------------------------------------
# lesson scope
# ---------------------------------------------------------------------------


async def test_generate_quiz_lesson_scope_returns_quiz_id() -> None:
    from lyw_core.worker.jobs.quiz import generate_quiz

    db = AsyncMock()
    db.get_lesson_graph.return_value = _graph([_concept("c1"), _concept("c2")])
    ctx = _make_ctx(db)

    mock_items = [_item("i1"), _item("i2")]

    with (
        patch("lyw_core.worker.jobs.quiz.MCQGenerator"),
        patch("lyw_core.worker.jobs.quiz.SectionQuizGenerator") as mock_qg,
    ):
        mock_qg.return_value.generate = AsyncMock(return_value=mock_items)
        result = await generate_quiz(ctx, lesson_id="lesson-1", profile_id="p1")

    assert result["quiz_id"] is not None
    assert set(result["item_ids"]) == {"i1", "i2"}
    assert result["concept_count"] == 2


async def test_generate_quiz_lesson_scope_calls_section_quiz_generator() -> None:
    from lyw_core.worker.jobs.quiz import generate_quiz

    db = AsyncMock()
    graph = _graph([_concept("c1")])
    db.get_lesson_graph.return_value = graph
    ctx = _make_ctx(db)

    with (
        patch("lyw_core.worker.jobs.quiz.MCQGenerator"),
        patch("lyw_core.worker.jobs.quiz.SectionQuizGenerator") as mock_qg_cls,
    ):
        gen_instance = mock_qg_cls.return_value
        gen_instance.generate = AsyncMock(return_value=[])
        await generate_quiz(ctx, lesson_id="lesson-1", profile_id="p1", scope="lesson")

    gen_instance.generate.assert_awaited_once()
    call_args = gen_instance.generate.call_args
    assert call_args[0][0] == [graph.concepts[0]]
    assert call_args[1]["quiz_id"] is not None


# ---------------------------------------------------------------------------
# concept scope
# ---------------------------------------------------------------------------


async def test_generate_quiz_concept_scope_uses_mcq_generator() -> None:
    from lyw_core.worker.jobs.quiz import generate_quiz

    db = AsyncMock()
    db.get_lesson_graph.return_value = _graph([_concept("c1"), _concept("c2")])
    ctx = _make_ctx(db)

    mock_mcq_items = [_item("i1")]

    with (
        patch("lyw_core.worker.jobs.quiz.MCQGenerator") as mock_mcq_cls,
        patch("lyw_core.worker.jobs.quiz.SectionQuizGenerator"),
    ):
        mock_mcq_cls.return_value.generate = AsyncMock(return_value=mock_mcq_items)
        result = await generate_quiz(
            ctx,
            lesson_id="lesson-1",
            profile_id="p1",
            concept_ids=["c1"],
            scope="concept",
        )

    assert result["quiz_id"] is None
    assert result["concept_count"] == 1
    assert result["item_ids"] == ["i1"]


async def test_generate_quiz_concept_scope_filters_targets() -> None:
    from lyw_core.worker.jobs.quiz import generate_quiz

    db = AsyncMock()
    db.get_lesson_graph.return_value = _graph([_concept("c1"), _concept("c2")])
    ctx = _make_ctx(db)

    with (
        patch("lyw_core.worker.jobs.quiz.MCQGenerator") as mock_mcq_cls,
        patch("lyw_core.worker.jobs.quiz.SectionQuizGenerator"),
    ):
        mock_mcq_cls.return_value.generate = AsyncMock(return_value=[])
        result = await generate_quiz(
            ctx,
            lesson_id="lesson-1",
            profile_id="p1",
            concept_ids=["c2"],
            scope="concept",
        )

    assert result["concept_count"] == 1


# ---------------------------------------------------------------------------
# error path
# ---------------------------------------------------------------------------


async def test_generate_quiz_lesson_not_found_returns_error() -> None:
    from lyw_core.worker.jobs.quiz import generate_quiz

    db = AsyncMock()
    db.get_lesson_graph.return_value = None
    ctx = _make_ctx(db)

    result = await generate_quiz(ctx, lesson_id="missing", profile_id="p1")

    assert "error" in result
