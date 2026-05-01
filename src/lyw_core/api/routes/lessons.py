"""Lessons endpoints — list, retrieve, and inspect lesson graphs."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from lesson_graph.models import ConceptNode, LessonGraph
from lyw_core.api.app import get_db
from lyw_core.api.schemas import StoredDerivedAsset
from lyw_core.db.dao import Database, DerivedAsset, LessonSummary

router = APIRouter()


class LessonSummaryResponse(BaseModel):
    id: str
    source_id: str
    concept_count: int
    created_at: str


@router.get(
    "/lessons",
    response_model=list[LessonSummaryResponse],
    operation_id="listLessons",
)
async def list_lessons(
    db: Annotated[Database, Depends(get_db)],
) -> list[LessonSummary]:
    return await db.list_lessons()


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


@router.get(
    "/lessons/{lesson_id}/concepts/{concept_id}",
    response_model=ConceptNode,
    operation_id="getConceptNode",
)
async def get_concept_node(
    lesson_id: str,
    concept_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> ConceptNode:
    graph = await db.get_lesson_graph(lesson_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    node = next((c for c in graph.concepts if c.id == concept_id), None)
    if node is None:
        raise HTTPException(status_code=404, detail="Concept not found")
    return node


@router.get(
    "/lessons/{lesson_id}/assets",
    response_model=list[StoredDerivedAsset],
    operation_id="listLessonAssets",
)
async def list_lesson_assets(
    lesson_id: str,
    db: Annotated[Database, Depends(get_db)],
    concept_id: Annotated[str | None, Query()] = None,
    kind: Annotated[str | None, Query()] = None,
    profile_id: Annotated[str | None, Query()] = None,
) -> list[DerivedAsset]:
    if await db.get_lesson_graph(lesson_id) is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return await db.list_derived_assets(
        lesson_id, concept_id=concept_id, kind=kind, profile_id=profile_id
    )
