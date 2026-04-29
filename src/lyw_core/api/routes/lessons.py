"""GET /lessons/{lesson_id} — retrieve the canonical lesson graph."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from lesson_graph.models import LessonGraph
from lyw_core.api.app import get_db
from lyw_core.db.dao import Database

router = APIRouter()


@router.get(
    "/lessons/{lesson_id}",
    response_model=LessonGraph,
    operation_id="getLesson",
)
async def get_lesson(
    lesson_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> LessonGraph:
    graph = await db.get_lesson_graph(lesson_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return graph
