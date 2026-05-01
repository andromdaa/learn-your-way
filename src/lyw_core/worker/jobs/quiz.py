"""Arq job: generate MCQ or section-quiz items for a lesson."""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from lyw_core.assessment.mcq import MCQGenerator
from lyw_core.assessment.quiz import SectionQuizGenerator
from lyw_core.db.dao import Database
from lyw_core.worker.jobs._progress import make_progress


async def generate_quiz(
    ctx: dict[str, Any],
    *,
    lesson_id: str,
    profile_id: str,
    concept_ids: list[str] | None = None,
    scope: Literal["concept", "lesson"] = "lesson",
) -> dict[str, Any]:
    progress = make_progress(ctx, lesson_id=lesson_id)
    db: Database = ctx["db"]
    model_client = ctx["model_client"]

    graph = await db.get_lesson_graph(lesson_id)
    if graph is None:
        await progress.fail(f"Lesson {lesson_id!r} not found")
        return {"error": "lesson not found"}

    targets = [
        c for c in graph.concepts if concept_ids is None or c.id in concept_ids
    ]
    quiz_id = uuid4().hex if scope == "lesson" else None
    mcq_gen = MCQGenerator(model_client=model_client, validators=[], dao=db)
    quiz_gen = SectionQuizGenerator(
        mcq_generator=mcq_gen, model_client=model_client, dao=db
    )

    if scope == "lesson":
        await progress.emit(phase="quiz_start", pct=0.0)
        items = await quiz_gen.generate(targets, graph, quiz_id=quiz_id)
    else:
        items = []
        for i, concept in enumerate(targets):
            await progress.emit(
                phase=f"mcq:{concept.id}", pct=i / max(len(targets), 1)
            )
            concept_items = await mcq_gen.generate(concept, graph)
            items.extend(concept_items)

    return await progress.done(
        {
            "quiz_id": quiz_id,
            "item_ids": [item.id for item in items],
            "concept_count": len(targets),
        }
    )
