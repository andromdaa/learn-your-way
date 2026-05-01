"""Unit tests for worker/jobs/bulk.py — bulk_generate job."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from lesson_graph.models import ConceptNode, LessonGraph, SourceSpan


def _concept(cid: str = "c1") -> ConceptNode:
    return ConceptNode(
        id=cid,
        title="T",
        summary="s",
        learning_objective="lo",
        source_spans=[SourceSpan(doc_id="d", page_start=1, page_end=1, char_start=0, char_end=5)],
    )


def _graph(concepts: list[ConceptNode] | None = None) -> LessonGraph:
    return LessonGraph(
        id="lesson-1", source_id="doc-1", concepts=concepts or [_concept()]
    )


def _make_ctx(db: AsyncMock | None = None, redis: AsyncMock | None = None) -> dict[str, Any]:
    mock_job = MagicMock()
    mock_job.job_id = "child-job-1"
    r = redis or AsyncMock()
    r.enqueue_job = AsyncMock(return_value=mock_job)
    return {
        "db": db or AsyncMock(),
        "redis": r,
        "progress_factory": None,
    }


# ---------------------------------------------------------------------------
# happy path
# ---------------------------------------------------------------------------


async def test_bulk_generate_enqueues_per_concept_kind() -> None:
    from lyw_core.worker.jobs.bulk import bulk_generate

    db = AsyncMock()
    db.get_lesson_graph.return_value = _graph([_concept("c1"), _concept("c2")])
    db.get_derived_asset.return_value = None
    ctx = _make_ctx(db)

    result = await bulk_generate(
        ctx, lesson_id="lesson-1", profile_id="p1", kinds=["relevel"], skip_existing=False
    )

    assert result["total"] == 2
    assert len(result["child_job_ids"]) == 2


async def test_bulk_generate_lesson_scoped_kind_uses_sentinel() -> None:
    from lyw_core.db.dao import LESSON_SCOPED_CONCEPT_ID
    from lyw_core.worker.jobs.bulk import bulk_generate

    db = AsyncMock()
    db.get_lesson_graph.return_value = _graph([_concept("c1")])
    db.get_derived_asset.return_value = None
    ctx = _make_ctx(db)

    await bulk_generate(
        ctx, lesson_id="lesson-1", profile_id="p1", kinds=["mind_map"], skip_existing=False
    )

    call_args = ctx["redis"].enqueue_job.call_args
    assert call_args[1]["concept_id"] == LESSON_SCOPED_CONCEPT_ID


async def test_bulk_generate_skip_existing_omits_already_done() -> None:
    from lyw_core.worker.jobs.bulk import bulk_generate

    db = AsyncMock()
    db.get_lesson_graph.return_value = _graph([_concept("c1"), _concept("c2")])
    db.get_derived_asset = AsyncMock(side_effect=lambda l, c, k, p: MagicMock() if c == "c1" else None)
    ctx = _make_ctx(db)

    result = await bulk_generate(
        ctx, lesson_id="lesson-1", profile_id="p1", kinds=["relevel"], skip_existing=True
    )

    assert result["total"] == 2
    assert len(result["child_job_ids"]) == 1


async def test_bulk_generate_skip_existing_false_enqueues_all() -> None:
    from lyw_core.worker.jobs.bulk import bulk_generate

    db = AsyncMock()
    db.get_lesson_graph.return_value = _graph([_concept("c1"), _concept("c2")])
    db.get_derived_asset.return_value = MagicMock()
    ctx = _make_ctx(db)

    result = await bulk_generate(
        ctx, lesson_id="lesson-1", profile_id="p1", kinds=["relevel"], skip_existing=False
    )

    assert len(result["child_job_ids"]) == 2


# ---------------------------------------------------------------------------
# error path
# ---------------------------------------------------------------------------


async def test_bulk_generate_lesson_not_found_returns_error() -> None:
    from lyw_core.worker.jobs.bulk import bulk_generate

    db = AsyncMock()
    db.get_lesson_graph.return_value = None
    ctx = _make_ctx(db)

    result = await bulk_generate(
        ctx, lesson_id="missing", profile_id="p1", kinds=["relevel"]
    )

    assert "error" in result
