"""POST /lessons/{lesson_id}/generate — enqueue a personalize_concept Arq job.

GET /lessons/{lesson_id}/generate/{job_id} — poll job status / fetch result.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from arq.connections import ArqRedis
from arq.jobs import Job, JobStatus
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lyw_core.api.app import get_arq_redis, get_db
from lyw_core.db.dao import Database

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    concept_id: str
    profile_id: str
    kind: Literal["relevel", "replace"]


class GenerateResponse(BaseModel):
    job_id: str
    status: str  # "queued"


class GenerateResultResponse(BaseModel):
    job_id: str
    status: str  # "pending" | "complete" | "not_found" | "failed"
    result: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/lessons/{lesson_id}/generate",
    status_code=202,
    response_model=GenerateResponse,
    operation_id="generateLesson",
)
async def generate_lesson(
    lesson_id: str,
    body: GenerateRequest,
    db: Annotated[Database, Depends(get_db)],
    arq_redis: Annotated[ArqRedis, Depends(get_arq_redis)],
) -> GenerateResponse:
    """Enqueue a personalize_concept job for a lesson concept.

    Returns 404 if the lesson does not exist.
    """
    graph = await db.get_lesson_graph(lesson_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Lesson not found")

    job: Job | None = await arq_redis.enqueue_job(
        "personalize_concept",
        lesson_id=lesson_id,
        concept_id=body.concept_id,
        profile_id=body.profile_id,
        kind=body.kind,
    )

    if job is None:
        raise HTTPException(status_code=409, detail="Duplicate job already queued")

    return GenerateResponse(job_id=job.job_id, status="queued")


@router.get(
    "/lessons/{lesson_id}/generate/{job_id}",
    response_model=GenerateResultResponse,
    operation_id="getGenerateResult",
)
async def get_generate_result(
    lesson_id: str,
    job_id: str,
    db: Annotated[Database, Depends(get_db)],
    arq_redis: Annotated[ArqRedis, Depends(get_arq_redis)],
) -> GenerateResultResponse:
    """Poll the status of a previously enqueued generate job.

    Returns ``status="pending"`` while the job is still running,
    ``status="complete"`` with the ``result`` payload when finished,
    and ``status="not_found"`` when no such job exists.
    """
    job = Job(job_id=job_id, redis=arq_redis)
    job_status: JobStatus = await job.status()

    if job_status == JobStatus.not_found:
        return GenerateResultResponse(job_id=job_id, status="not_found")

    if job_status != JobStatus.complete:
        return GenerateResultResponse(job_id=job_id, status="pending")

    # Job is complete — retrieve the stored result payload
    info = await job.result_info()

    if info is not None and not info.success:
        return GenerateResultResponse(
            job_id=job_id,
            status="failed",
            result={"error": repr(info.result)},
        )

    result: dict[str, Any] | None = None
    if info is not None and info.result is not None:
        result = dict(info.result)

    return GenerateResultResponse(job_id=job_id, status="complete", result=result)
