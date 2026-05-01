"""Quiz endpoints — generate, retrieve, and post-quiz Glows/Grows."""

from __future__ import annotations

import dataclasses
from typing import Annotated, Literal

import structlog
from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from lesson_graph.models import AssessmentItem
from lyw_core.api.app import get_arq_redis, get_db
from lyw_core.assessment.mcq import MCQGenerator
from lyw_core.assessment.quiz import SectionQuizGenerator
from lyw_core.clients.ollama import OllamaModelClient
from lyw_core.db.dao import AttemptRecord, Database
from lyw_core.settings import Settings

_logger = structlog.get_logger(__name__)

router = APIRouter()


class QuizGenerateRequest(BaseModel):
    profile_id: str
    scope: Literal["concept", "lesson"] = "lesson"
    concept_ids: list[str] | None = None


class McqGenerateRequest(BaseModel):
    profile_id: str


class BulkGenerateRequest(BaseModel):
    profile_id: str
    kinds: list[str]
    skip_existing: bool = True


class JobEnqueuedResponse(BaseModel):
    job_id: str
    status: str = "queued"


class GlowsGrowsRequest(BaseModel):
    profile_id: str


class GlowsGrowsResponse(BaseModel):
    glows: str
    grows: str


class AttemptResponse(BaseModel):
    id: str
    profile_id: str
    item_id: str
    response: str
    correct: bool
    attempted_at: str


@router.post(
    "/lessons/{lesson_id}/quiz",
    status_code=202,
    response_model=JobEnqueuedResponse,
    operation_id="generateQuiz",
)
async def generate_quiz_route(
    lesson_id: str,
    body: QuizGenerateRequest,
    db: Annotated[Database, Depends(get_db)],
    arq_redis: Annotated[ArqRedis, Depends(get_arq_redis)],
) -> JobEnqueuedResponse:
    if await db.get_lesson_graph(lesson_id) is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    job = await arq_redis.enqueue_job(
        "generate_quiz",
        lesson_id=lesson_id,
        profile_id=body.profile_id,
        concept_ids=body.concept_ids,
        scope=body.scope,
    )
    if job is None:
        raise HTTPException(status_code=409, detail="Duplicate job already queued")
    return JobEnqueuedResponse(job_id=job.job_id)


@router.post(
    "/lessons/{lesson_id}/concepts/{concept_id}/mcq",
    status_code=202,
    response_model=JobEnqueuedResponse,
    operation_id="generateMcq",
)
async def generate_mcq_route(
    lesson_id: str,
    concept_id: str,
    body: McqGenerateRequest,
    db: Annotated[Database, Depends(get_db)],
    arq_redis: Annotated[ArqRedis, Depends(get_arq_redis)],
) -> JobEnqueuedResponse:
    graph = await db.get_lesson_graph(lesson_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if not any(c.id == concept_id for c in graph.concepts):
        raise HTTPException(status_code=404, detail="Concept not found")
    job = await arq_redis.enqueue_job(
        "generate_quiz",
        lesson_id=lesson_id,
        profile_id=body.profile_id,
        concept_ids=[concept_id],
        scope="concept",
    )
    if job is None:
        raise HTTPException(status_code=409, detail="Duplicate job already queued")
    return JobEnqueuedResponse(job_id=job.job_id)


@router.get(
    "/lessons/{lesson_id}/quiz/{quiz_id}",
    response_model=list[AssessmentItem],
    operation_id="getQuiz",
)
async def get_quiz(
    lesson_id: str,
    quiz_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> list[AssessmentItem]:
    if await db.get_lesson_graph(lesson_id) is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    items = await db.get_items_by_quiz_id(quiz_id)
    if not items:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return items


@router.get(
    "/attempts/by-quiz",
    response_model=list[AttemptResponse],
    operation_id="getAttemptsByQuiz",
)
async def get_attempts_by_quiz(
    quiz_id: Annotated[str, Query()],
    profile_id: Annotated[str, Query()],
    db: Annotated[Database, Depends(get_db)],
) -> list[AttemptRecord]:
    return await db.get_attempts_by_quiz_id(quiz_id, profile_id)


@router.post(
    "/quizzes/{quiz_id}/glows-grows",
    response_model=GlowsGrowsResponse,
    operation_id="generateGlowsGrows",
)
async def generate_glows_grows_route(
    quiz_id: str,
    body: GlowsGrowsRequest,
    db: Annotated[Database, Depends(get_db)],
) -> GlowsGrowsResponse:
    items = await db.get_items_by_quiz_id(quiz_id)
    if not items:
        raise HTTPException(status_code=404, detail="Quiz not found")
    attempts = await db.get_attempts_by_quiz_id(quiz_id, body.profile_id)
    settings = Settings()
    model_client = OllamaModelClient(
        base_url=settings.ollama_base_url,
        model=settings.model_name,
    )
    mcq_gen = MCQGenerator(model_client=model_client, validators=[], dao=db)
    quiz_gen = SectionQuizGenerator(
        mcq_generator=mcq_gen, model_client=model_client, dao=db
    )
    try:
        feedback = await quiz_gen.generate_glows_grows(items, attempts)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    gg = dataclasses.asdict(feedback)
    return GlowsGrowsResponse(glows=gg["glows"], grows=gg["grows"])


@router.post(
    "/lessons/{lesson_id}/bulk-generate",
    status_code=202,
    response_model=JobEnqueuedResponse,
    operation_id="bulkGenerate",
)
async def bulk_generate_route(
    lesson_id: str,
    body: BulkGenerateRequest,
    db: Annotated[Database, Depends(get_db)],
    arq_redis: Annotated[ArqRedis, Depends(get_arq_redis)],
) -> JobEnqueuedResponse:
    if await db.get_lesson_graph(lesson_id) is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    job = await arq_redis.enqueue_job(
        "bulk_generate",
        lesson_id=lesson_id,
        profile_id=body.profile_id,
        kinds=body.kinds,
        skip_existing=body.skip_existing,
    )
    if job is None:
        raise HTTPException(status_code=409, detail="Duplicate job already queued")
    return JobEnqueuedResponse(job_id=job.job_id)
