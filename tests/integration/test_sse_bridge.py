"""Integration tests for the SSE bridge — requires Redis via testcontainers."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.integration

try:
    from testcontainers.redis import RedisContainer

    _HAVE_TESTCONTAINERS = True
except ImportError:
    _HAVE_TESTCONTAINERS = False

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from lyw_core.api.app import create_app, get_arq_redis, get_db  # noqa: E402


@asynccontextmanager
async def _null_lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


def _make_client(arq_redis: Any) -> TestClient:
    mock_db = AsyncMock()
    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: arq_redis
    return TestClient(_app)


@pytest.fixture(scope="module")
def redis_container_url() -> Generator[str, None, None]:
    if not _HAVE_TESTCONTAINERS:
        pytest.skip("testcontainers not installed")
    try:
        with RedisContainer("redis:7-alpine") as container:
            host = container.get_container_host_ip()
            port = container.get_exposed_port(6379)
            yield f"redis://{host}:{port}/0"
    except Exception as exc:
        pytest.skip(f"Docker not available: {exc}")


def test_sse_job_events_content_type_with_real_redis(redis_container_url: str) -> None:
    """SSE endpoint returns text/event-stream when backed by a real Redis."""
    import asyncio

    import redis.asyncio as aioredis

    class _FakeArq:
        """Minimal wrapper around aioredis to satisfy the SSE bridge."""

        def __init__(self, r: Any) -> None:
            self._r = r

        def pubsub(self) -> Any:
            return self._r.pubsub()

    async def _setup() -> _FakeArq:
        r = await aioredis.from_url(redis_container_url)
        return _FakeArq(r)

    arq = asyncio.run(_setup())

    # Background thread publishes a complete event after 200ms so the SSE stream closes.
    def _publish() -> None:
        time.sleep(0.2)

        async def _do() -> None:
            import redis.asyncio as _r

            client = await _r.from_url(redis_container_url)
            await client.publish(
                "lyw:job:sse-test-job",
                json.dumps({"event": "complete", "job_id": "sse-test-job"}),
            )
            await client.aclose()

        asyncio.run(_do())

    t = threading.Thread(target=_publish, daemon=True)
    t.start()

    with _make_client(arq) as c:  # noqa: SIM117
        with c.stream("GET", "/v1/jobs/sse-test-job/events") as resp:
            assert resp.headers["content-type"].startswith("text/event-stream")
            lines = list(resp.iter_lines())

    t.join(timeout=2)
    assert any("complete" in line for line in lines)


def test_sse_global_events_content_type_with_real_redis(redis_container_url: str) -> None:
    """Global /v1/jobs/events SSE endpoint returns text/event-stream."""
    import asyncio

    import redis.asyncio as aioredis

    class _FakeArq:
        def __init__(self, r: Any) -> None:
            self._r = r

        def pubsub(self) -> Any:
            return self._r.pubsub()

    async def _setup() -> _FakeArq:
        r = await aioredis.from_url(redis_container_url)
        return _FakeArq(r)

    arq = asyncio.run(_setup())

    def _publish() -> None:
        time.sleep(0.2)

        async def _do() -> None:
            import redis.asyncio as _r

            client = await _r.from_url(redis_container_url)
            await client.publish(
                "lyw:jobs:all",
                json.dumps({"event": "complete", "job_id": "any"}),
            )
            await client.aclose()

        asyncio.run(_do())

    t = threading.Thread(target=_publish, daemon=True)
    t.start()

    with _make_client(arq) as c, c.stream("GET", "/v1/jobs/events") as resp:
        assert resp.headers["content-type"].startswith("text/event-stream")

    t.join(timeout=2)
