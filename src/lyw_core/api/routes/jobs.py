"""SSE job-events endpoints and job result endpoint."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated, Any

from arq.connections import ArqRedis
from arq.jobs import Job, JobStatus
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from lyw_core.api.app import get_arq_redis

router = APIRouter()

_TERMINAL_EVENTS = frozenset({"complete", "error"})


class JobResultResponse(BaseModel):
    status: str
    result: Any = None
    error: str | None = None
    traceback: str | None = None


async def _pubsub_gen(
    request: Request,
    arq_redis: ArqRedis,
    channel: str,
) -> AsyncIterator[dict[str, str]]:
    async with arq_redis.pubsub() as ps:
        await ps.subscribe(channel)
        async for msg in ps.listen():
            if await request.is_disconnected():
                break
            if msg["type"] != "message":
                continue
            payload: dict[str, Any] = json.loads(msg["data"])
            yield {
                "event": payload.get("event", "progress"),
                "data": json.dumps(payload),
            }
            if payload.get("event") in _TERMINAL_EVENTS:
                break


@router.get("/v1/jobs/{job_id}/events", operation_id="streamJobEvents")
async def stream_job_events(
    job_id: str,
    request: Request,
    arq_redis: Annotated[ArqRedis, Depends(get_arq_redis)],
) -> EventSourceResponse:
    return EventSourceResponse(_pubsub_gen(request, arq_redis, f"lyw:job:{job_id}"))


@router.get(
    "/v1/lessons/{lesson_id}/jobs/events",
    operation_id="streamLessonJobEvents",
)
async def stream_lesson_job_events(
    lesson_id: str,
    request: Request,
    arq_redis: Annotated[ArqRedis, Depends(get_arq_redis)],
) -> EventSourceResponse:
    return EventSourceResponse(
        _pubsub_gen(request, arq_redis, f"lyw:lesson:{lesson_id}")
    )


@router.get("/v1/jobs/events", operation_id="streamAllJobEvents")
async def stream_all_job_events(
    request: Request,
    arq_redis: Annotated[ArqRedis, Depends(get_arq_redis)],
) -> EventSourceResponse:
    return EventSourceResponse(_pubsub_gen(request, arq_redis, "lyw:jobs:all"))


@router.get(
    "/v1/jobs/{job_id}/result",
    response_model=JobResultResponse,
    operation_id="getJobResult",
)
async def get_job_result(
    job_id: str,
    arq_redis: Annotated[ArqRedis, Depends(get_arq_redis)],
) -> JobResultResponse:
    job = Job(job_id, arq_redis)
    status = await job.status()
    if status == JobStatus.not_found:
        raise HTTPException(status_code=404, detail="Job not found")
    if status not in (JobStatus.complete,):
        return JobResultResponse(status=status.value)
    info = await job.info()
    if info is None:
        return JobResultResponse(status="complete")
    if info.success:  # type: ignore[attr-defined]
        return JobResultResponse(status="complete", result=info.result)  # type: ignore[attr-defined]
    return JobResultResponse(
        status="failed",
        error=str(info.result) if info.result is not None else None,  # type: ignore[attr-defined]
        traceback=info.traceback,  # type: ignore[attr-defined]
    )
