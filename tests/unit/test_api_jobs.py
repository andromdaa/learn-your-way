"""Unit tests for SSE job-events routes and GET /v1/jobs/{id}/result."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arq.jobs import JobStatus
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lyw_core.api.app import create_app, get_arq_redis, get_db


@asynccontextmanager
async def _null_lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


def _make_client(mock_arq: AsyncMock) -> TestClient:
    mock_db = AsyncMock()
    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: mock_arq
    return TestClient(_app)


# ---------------------------------------------------------------------------
# GET /v1/jobs/{job_id}/result
# ---------------------------------------------------------------------------


def test_get_job_result_not_found_returns_404() -> None:
    mock_arq = AsyncMock()

    with patch("lyw_core.api.routes.jobs.Job") as mock_job_cls:
        mock_job = AsyncMock()
        mock_job.status.return_value = JobStatus.not_found
        mock_job_cls.return_value = mock_job

        with _make_client(mock_arq) as c:
            response = c.get("/v1/jobs/j-unknown/result")
    assert response.status_code == 404


def test_get_job_result_in_progress_returns_status() -> None:
    mock_arq = AsyncMock()

    with patch("lyw_core.api.routes.jobs.Job") as mock_job_cls:
        mock_job = AsyncMock()
        mock_job.status.return_value = JobStatus.in_progress
        mock_job_cls.return_value = mock_job

        with _make_client(mock_arq) as c:
            response = c.get("/v1/jobs/j-running/result")
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_get_job_result_complete_returns_result() -> None:
    mock_arq = AsyncMock()

    info = MagicMock()
    info.success = True
    info.result = {"lesson_id": "l1", "concept_count": 3}
    info.traceback = None

    with patch("lyw_core.api.routes.jobs.Job") as mock_job_cls:
        mock_job = AsyncMock()
        mock_job.status.return_value = JobStatus.complete
        mock_job.info.return_value = info
        mock_job_cls.return_value = mock_job

        with _make_client(mock_arq) as c:
            response = c.get("/v1/jobs/j-done/result")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "complete"
    assert body["result"]["lesson_id"] == "l1"


def test_get_job_result_failed_returns_error() -> None:
    mock_arq = AsyncMock()

    info = MagicMock()
    info.success = False
    info.result = "ValueError: lesson not found"
    info.traceback = "Traceback...\nValueError: lesson not found"

    with patch("lyw_core.api.routes.jobs.Job") as mock_job_cls:
        mock_job = AsyncMock()
        mock_job.status.return_value = JobStatus.complete
        mock_job.info.return_value = info
        mock_job_cls.return_value = mock_job

        with _make_client(mock_arq) as c:
            response = c.get("/v1/jobs/j-failed/result")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert "ValueError" in body["error"]
    assert body["traceback"] is not None


# ---------------------------------------------------------------------------
# SSE streaming routes — verify content-type header
# ---------------------------------------------------------------------------


def _make_mock_pubsub() -> AsyncMock:
    """Returns a mock pubsub context manager that emits one complete event."""

    class _MockPS:
        async def subscribe(self, *_channels: str) -> None:
            pass

        async def __aenter__(self) -> "_MockPS":
            return self

        async def __aexit__(self, *_args: object) -> None:
            pass

        async def listen(self) -> AsyncIterator[dict]:
            import json

            yield {
                "type": "message",
                "data": json.dumps({"event": "complete", "job_id": "j1"}).encode(),
            }

    mock = AsyncMock()
    mock.pubsub = MagicMock(return_value=_MockPS())
    return mock


def test_stream_job_events_returns_event_stream() -> None:
    mock_arq = _make_mock_pubsub()
    with _make_client(mock_arq) as c:
        with c.stream("GET", "/v1/jobs/j1/events") as response:
            assert response.headers["content-type"].startswith("text/event-stream")


def test_stream_lesson_job_events_returns_event_stream() -> None:
    mock_arq = _make_mock_pubsub()
    with _make_client(mock_arq) as c:
        with c.stream("GET", "/v1/lessons/l1/jobs/events") as response:
            assert response.headers["content-type"].startswith("text/event-stream")


def test_stream_all_job_events_returns_event_stream() -> None:
    mock_arq = _make_mock_pubsub()
    with _make_client(mock_arq) as c:
        with c.stream("GET", "/v1/jobs/events") as response:
            assert response.headers["content-type"].startswith("text/event-stream")
