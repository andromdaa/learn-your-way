"""Arq job: fan-out personalize_concept for every (concept, kind) in a lesson."""

from __future__ import annotations

from typing import Any

from lyw_core.db.dao import LESSON_SCOPED_CONCEPT_ID, Database
from lyw_core.worker.jobs._progress import make_progress

_LESSON_SCOPED_KINDS = frozenset({"mind_map", "timeline"})


async def bulk_generate(
    ctx: dict[str, Any],
    *,
    lesson_id: str,
    profile_id: str,
    kinds: list[str],
    skip_existing: bool = True,
) -> dict[str, Any]:
    progress = make_progress(ctx, lesson_id=lesson_id)
    db: Database = ctx["db"]
    redis = ctx["redis"]

    graph = await db.get_lesson_graph(lesson_id)
    if graph is None:
        await progress.fail(f"Lesson {lesson_id!r} not found")
        return {"error": "lesson not found"}

    matrix: list[tuple[str, str]] = []
    for kind in kinds:
        if kind in _LESSON_SCOPED_KINDS:
            matrix.append((LESSON_SCOPED_CONCEPT_ID, kind))
        else:
            for concept in graph.concepts:
                matrix.append((concept.id, kind))

    child_ids: list[str] = []
    total = len(matrix)

    for i, (cid, kind) in enumerate(matrix):
        pct = (i + 1) / max(total, 1)
        if skip_existing:
            existing = await db.get_derived_asset(lesson_id, cid, kind, profile_id)
            if existing is not None:
                await progress.emit(
                    phase="skip", pct=pct, data={"cid": cid, "kind": kind}
                )
                continue
        job = await redis.enqueue_job(
            "personalize_concept",
            lesson_id=lesson_id,
            concept_id=cid,
            profile_id=profile_id,
            kind=kind,
        )
        if job is not None:
            child_ids.append(job.job_id)
        await progress.emit(phase="enqueue", pct=pct, data={"cid": cid, "kind": kind})

    return await progress.done({"child_job_ids": child_ids, "total": total})
