"""Job progress publisher — emits SSE-compatible events to Redis pub/sub.

Workers call ``make_progress(ctx, lesson_id)`` to obtain either a real
``JobProgress`` (when the worker context has ``"progress_factory"`` set) or
a ``NoopProgress`` that discards every call.
"""

from __future__ import annotations

import json
from typing import Any


class JobProgress:
    """Publishes progress events to Redis channels for a single job."""

    def __init__(
        self,
        redis: Any,
        *,
        job_id: str,
        lesson_id: str | None = None,
    ) -> None:
        self._redis = redis
        self._job_id = job_id
        self._lesson_id = lesson_id

    async def emit(
        self,
        *,
        phase: str,
        pct: float,
        msg: str = "",
        data: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "event": "progress",
            "job_id": self._job_id,
            "phase": phase,
            "pct": pct,
            "msg": msg,
        }
        if data:
            payload.update(data)
        await self._publish(payload)

    async def fail(
        self,
        error: str,
        *,
        traceback: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "event": "error",
            "job_id": self._job_id,
            "error": error,
        }
        if traceback is not None:
            payload["traceback"] = traceback
        if details:
            payload.update(details)
        await self._publish(payload)

    async def done(self, result: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "event": "complete",
            "job_id": self._job_id,
            **result,
        }
        await self._publish(payload)
        return result

    async def _publish(self, payload: dict[str, Any]) -> None:
        msg = json.dumps(payload)
        await self._redis.publish(f"lyw:job:{self._job_id}", msg)
        if self._lesson_id is not None:
            await self._redis.publish(f"lyw:lesson:{self._lesson_id}", msg)
        await self._redis.publish("lyw:jobs:all", msg)


class NoopProgress:
    """Drop-in for JobProgress used when no Redis connection is available."""

    async def emit(
        self,
        *,
        phase: str,
        pct: float,
        msg: str = "",
        data: dict[str, Any] | None = None,
    ) -> None:
        pass

    async def fail(
        self,
        error: str,
        *,
        traceback: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        pass

    async def done(self, result: dict[str, Any]) -> dict[str, Any]:
        return result


def make_progress(
    ctx: dict[str, Any],
    lesson_id: str | None = None,
) -> JobProgress | NoopProgress:
    """Return a JobProgress if ``progress_factory`` is in ctx, else NoopProgress."""
    factory = ctx.get("progress_factory")
    if factory is not None:
        job_id: str = ctx.get("job_id", "unknown")
        return factory(job_id, lesson_id=lesson_id)  # type: ignore[no-any-return]
    return NoopProgress()
