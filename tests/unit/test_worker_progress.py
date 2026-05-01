"""Unit tests for _progress.py — JobProgress and NoopProgress."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

from lyw_core.worker.jobs._progress import JobProgress, NoopProgress, make_progress

# ---------------------------------------------------------------------------
# NoopProgress — just verifies it accepts all calls without error
# ---------------------------------------------------------------------------


async def test_noop_progress_emit_returns_none() -> None:
    p = NoopProgress()
    await p.emit(phase="test", pct=0.5)


async def test_noop_progress_fail_returns_none() -> None:
    p = NoopProgress()
    await p.fail("boom", traceback="tb")


async def test_noop_progress_done_returns_result() -> None:
    p = NoopProgress()
    result = await p.done({"x": 1})
    assert result == {"x": 1}


# ---------------------------------------------------------------------------
# make_progress factory
# ---------------------------------------------------------------------------


async def test_make_progress_without_factory_returns_noop() -> None:
    ctx: dict[str, object] = {}
    p = make_progress(ctx)
    assert isinstance(p, NoopProgress)


async def test_make_progress_with_factory_returns_job_progress() -> None:
    redis = AsyncMock()
    redis.publish = AsyncMock()

    def factory(job_id: str, lesson_id: str | None = None) -> JobProgress:
        return JobProgress(redis, job_id=job_id, lesson_id=lesson_id)

    ctx = {"progress_factory": factory, "job_id": "j1"}
    p = make_progress(ctx, lesson_id="lesson-1")
    assert isinstance(p, JobProgress)


# ---------------------------------------------------------------------------
# JobProgress — verifies Redis publish calls
# ---------------------------------------------------------------------------


async def test_job_progress_emit_publishes_to_job_channel() -> None:
    redis = AsyncMock()
    p = JobProgress(redis, job_id="j1")
    await p.emit(phase="parse_start", pct=0.0)

    calls = [call.args[0] for call in redis.publish.await_args_list]
    assert "lyw:job:j1" in calls
    assert "lyw:jobs:all" in calls


async def test_job_progress_emit_also_publishes_lesson_channel_when_set() -> None:
    redis = AsyncMock()
    p = JobProgress(redis, job_id="j1", lesson_id="l1")
    await p.emit(phase="parse_start", pct=0.1)

    channels = {call.args[0] for call in redis.publish.await_args_list}
    assert "lyw:lesson:l1" in channels


async def test_job_progress_emit_payload() -> None:
    redis = AsyncMock()
    p = JobProgress(redis, job_id="j1")
    await p.emit(phase="chunk_done", pct=0.5, msg="done", data={"concepts": 3})

    raw = redis.publish.await_args_list[0].args[1]
    payload = json.loads(raw)
    assert payload["event"] == "progress"
    assert payload["phase"] == "chunk_done"
    assert payload["pct"] == 0.5
    assert payload["concepts"] == 3


async def test_job_progress_fail_publishes_error_event() -> None:
    redis = AsyncMock()
    p = JobProgress(redis, job_id="j1")
    await p.fail("oops", traceback="line 1\nline 2")

    raw = redis.publish.await_args_list[0].args[1]
    payload = json.loads(raw)
    assert payload["event"] == "error"
    assert payload["error"] == "oops"
    assert payload["traceback"] == "line 1\nline 2"


async def test_job_progress_done_publishes_complete_event_and_returns_result() -> None:
    redis = AsyncMock()
    p = JobProgress(redis, job_id="j1")
    result = await p.done({"lesson_id": "l1", "concept_count": 5})

    assert result == {"lesson_id": "l1", "concept_count": 5}

    raw = redis.publish.await_args_list[0].args[1]
    payload = json.loads(raw)
    assert payload["event"] == "complete"
    assert payload["lesson_id"] == "l1"
