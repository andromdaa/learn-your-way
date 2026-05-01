"""Unit tests for POST /lessons/{id}/generate and GET /lessons/{id}/generate/{job_id}.

All DB, Arq pool, and job state are mocked — no real workers or Redis.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from arq.jobs import JobStatus
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lesson_graph import ConceptNode, LessonGraph, SourceSpan
from lyw_core.api.app import create_app, get_arq_redis, get_db


@asynccontextmanager
async def _null_lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


def _span() -> SourceSpan:
    return SourceSpan(
        doc_id="doc-1", page_start=1, page_end=1, char_start=0, char_end=50
    )


def _graph() -> LessonGraph:
    return LessonGraph(
        id="lesson-1",
        source_id="doc-1",
        concepts=[
            ConceptNode(
                id="c1",
                title="Concept One",
                summary="Summary.",
                learning_objective="Understand it.",
                source_spans=[_span()],
                prerequisites=[],
            )
        ],
    )


def _make_mock_job(job_id: str = "job-abc") -> MagicMock:
    """Return a mock arq Job with a job_id attribute."""
    mock_job = MagicMock()
    mock_job.job_id = job_id
    return mock_job


@pytest.fixture()
def client() -> Iterator[TestClient]:
    """Default client: lesson exists, arq returns a fresh job on enqueue."""
    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = _graph()

    mock_job = _make_mock_job("job-abc")
    mock_arq = AsyncMock()
    mock_arq.enqueue_job.return_value = mock_job

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: mock_arq

    with TestClient(_app) as c:
        yield c


# ---------------------------------------------------------------------------
# POST /lessons/{lesson_id}/generate
# ---------------------------------------------------------------------------


def test_post_generate_returns_202(client: TestClient) -> None:
    response = client.post(
        "/lessons/lesson-1/generate",
        json={"concept_id": "c1", "profile_id": "p1", "kind": "mnemonic"},
    )
    assert response.status_code == 202


def test_post_generate_response_schema(client: TestClient) -> None:
    response = client.post(
        "/lessons/lesson-1/generate",
        json={"concept_id": "c1", "profile_id": "p1", "kind": "mnemonic"},
    )
    body = response.json()
    assert body["job_id"] == "job-abc"
    assert body["status"] == "queued"


def test_post_generate_enqueues_correct_job(client: TestClient) -> None:
    """The arq pool must be called with the right function name and kwargs."""
    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = _graph()

    mock_job = _make_mock_job("job-xyz")
    mock_arq = AsyncMock()
    mock_arq.enqueue_job.return_value = mock_job

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: mock_arq

    with TestClient(_app) as c:
        c.post(
            "/lessons/lesson-1/generate",
            json={"concept_id": "c1", "profile_id": "p1", "kind": "relevel"},
        )

    mock_arq.enqueue_job.assert_awaited_once_with(
        "personalize_concept",
        lesson_id="lesson-1",
        concept_id="c1",
        profile_id="p1",
        kind="relevel",
    )


def test_post_generate_lesson_not_found_returns_404() -> None:
    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = None

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()

    with TestClient(_app) as c:
        response = c.post(
            "/lessons/nonexistent/generate",
            json={"concept_id": "c1", "profile_id": "p1", "kind": "mnemonic"},
        )
    assert response.status_code == 404


def test_post_generate_invalid_kind_returns_422(client: TestClient) -> None:
    response = client.post(
        "/lessons/lesson-1/generate",
        json={"concept_id": "c1", "profile_id": "p1", "kind": "invalid_kind"},
    )
    assert response.status_code == 422


def test_post_generate_all_valid_kinds(client: TestClient) -> None:
    for kind in ("relevel", "replace", "mnemonic", "mind_map", "timeline", "slides"):
        response = client.post(
            "/lessons/lesson-1/generate",
            json={"concept_id": "c1", "profile_id": "p1", "kind": kind},
        )
        assert response.status_code == 202, f"kind={kind!r} should be accepted"


def test_post_generate_slides_returns_202_and_job_id(client: TestClient) -> None:
    """POST with kind='slides' returns 202 and a job_id immediately."""
    response = client.post(
        "/lessons/lesson-1/generate",
        json={
            "concept_id": "__lesson__",
            "profile_id": "p1",
            "kind": "slides",
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert "job_id" in body
    assert body["job_id"] == "job-abc"
    assert body["status"] == "queued"


def test_post_generate_timeline_returns_202_and_job_id(client: TestClient) -> None:
    """POST with kind='timeline' returns 202 and a job_id immediately.

    Confirms the timeline kind is accepted by the API layer and enqueued
    without waiting for generation (which may result in TimelineSkipped).
    """
    response = client.post(
        "/lessons/lesson-1/generate",
        json={
            "concept_id": "__lesson__",
            "profile_id": "p1",
            "kind": "timeline",
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert "job_id" in body
    assert body["job_id"] == "job-abc"
    assert body["status"] == "queued"


def test_post_generate_mind_map_returns_202_and_job_id(client: TestClient) -> None:
    """POST with kind='mind_map' returns 202 and a job_id immediately.

    Asserts the endpoint is non-blocking: it enqueues the job and responds
    without waiting for generation to complete.  The mock arq queue returns
    synchronously, confirming the route layer does not await any generator work.
    """
    response = client.post(
        "/lessons/lesson-1/generate",
        json={
            "concept_id": "__lesson__",
            "profile_id": "p1",
            "kind": "mind_map",
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert "job_id" in body
    assert body["job_id"] == "job-abc"
    assert body["status"] == "queued"


def test_post_generate_duplicate_job_returns_409() -> None:
    """When arq.enqueue_job returns None (duplicate), the endpoint returns 409."""
    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = _graph()

    mock_arq = AsyncMock()
    mock_arq.enqueue_job.return_value = None  # arq signals duplicate

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: mock_arq

    with TestClient(_app) as c:
        response = c.post(
            "/lessons/lesson-1/generate",
            json={"concept_id": "c1", "profile_id": "p1", "kind": "mnemonic"},
        )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# GET /lessons/{lesson_id}/generate/{job_id}
# ---------------------------------------------------------------------------


def test_get_generate_result_pending() -> None:
    """While job is in_progress the endpoint returns status=pending."""
    import unittest.mock as _mock

    mock_db = AsyncMock()
    mock_arq = AsyncMock()

    mock_job = AsyncMock()
    mock_job.status = AsyncMock(return_value=JobStatus.in_progress)
    mock_job.result_info = AsyncMock(return_value=None)

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: mock_arq

    with (
        _mock.patch("lyw_core.api.routes.generate.Job", return_value=mock_job),
        TestClient(_app) as c,
    ):
        response = c.get("/lessons/lesson-1/generate/job-abc")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["job_id"] == "job-abc"
    assert body["result"] is None


def test_get_generate_result_queued_returns_pending() -> None:
    """A queued (not yet started) job also returns status=pending."""
    import unittest.mock as _mock

    mock_db = AsyncMock()
    mock_arq = AsyncMock()

    mock_job = AsyncMock()
    mock_job.status = AsyncMock(return_value=JobStatus.queued)
    mock_job.result_info = AsyncMock(return_value=None)

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: mock_arq

    with (
        _mock.patch("lyw_core.api.routes.generate.Job", return_value=mock_job),
        TestClient(_app) as c,
    ):
        response = c.get("/lessons/lesson-1/generate/job-abc")

    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_get_generate_result_not_found() -> None:
    """Unknown job_id returns status=not_found."""
    import unittest.mock as _mock

    mock_db = AsyncMock()
    mock_arq = AsyncMock()

    mock_job = AsyncMock()
    mock_job.status = AsyncMock(return_value=JobStatus.not_found)
    mock_job.result_info = AsyncMock(return_value=None)

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: mock_arq

    with (
        _mock.patch("lyw_core.api.routes.generate.Job", return_value=mock_job),
        TestClient(_app) as c,
    ):
        response = c.get("/lessons/lesson-1/generate/no-such-job")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_found"
    assert body["result"] is None


def test_get_generate_result_complete_with_payload() -> None:
    """A complete job returns status=complete and the result dict."""
    import unittest.mock as _mock

    mock_db = AsyncMock()
    mock_arq = AsyncMock()

    mock_result_info = MagicMock()
    mock_result_info.result = {"asset_id": "a1", "file_path": "/data/assets/x.txt"}

    mock_job = AsyncMock()
    mock_job.status = AsyncMock(return_value=JobStatus.complete)
    mock_job.result_info = AsyncMock(return_value=mock_result_info)

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: mock_arq

    with (
        _mock.patch("lyw_core.api.routes.generate.Job", return_value=mock_job),
        TestClient(_app) as c,
    ):
        response = c.get("/lessons/lesson-1/generate/job-done")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "complete"
    assert body["job_id"] == "job-done"
    assert body["result"] == {"asset_id": "a1", "file_path": "/data/assets/x.txt"}


def test_get_generate_result_complete_no_result_info() -> None:
    """A complete job with no result_info still returns status=complete."""
    import unittest.mock as _mock

    mock_db = AsyncMock()
    mock_arq = AsyncMock()

    mock_job = AsyncMock()
    mock_job.status = AsyncMock(return_value=JobStatus.complete)
    mock_job.result_info = AsyncMock(return_value=None)

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: mock_arq

    with (
        _mock.patch("lyw_core.api.routes.generate.Job", return_value=mock_job),
        TestClient(_app) as c,
    ):
        response = c.get("/lessons/lesson-1/generate/job-done")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "complete"
    assert body["result"] is None


def test_get_generate_result_failed_with_validation_error() -> None:
    """When the job raised a ValidationError, endpoint returns status=failed with error repr."""
    import unittest.mock as _mock

    from pydantic import BaseModel as _PydanticBase
    from pydantic import ValidationError

    # Construct a real ValidationError via a Pydantic model
    class _M(_PydanticBase):
        x: int

    try:
        _M(x="not-an-int")
    except ValidationError as exc:
        raised_exc = exc

    mock_db = AsyncMock()
    mock_arq = AsyncMock()

    mock_result_info = MagicMock()
    mock_result_info.success = False
    mock_result_info.result = raised_exc

    mock_job = AsyncMock()
    mock_job.status = AsyncMock(return_value=JobStatus.complete)
    mock_job.result_info = AsyncMock(return_value=mock_result_info)

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: mock_arq

    with (
        _mock.patch("lyw_core.api.routes.generate.Job", return_value=mock_job),
        TestClient(_app) as c,
    ):
        response = c.get("/lessons/lesson-1/generate/job-failed")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["job_id"] == "job-failed"
    assert "error" in body["result"]
    assert "validation error" in body["result"]["error"].lower()


def test_get_generate_result_failed_with_arbitrary_exception() -> None:
    """When the job raised an arbitrary exception, endpoint returns status=failed."""
    import unittest.mock as _mock

    mock_db = AsyncMock()
    mock_arq = AsyncMock()

    raised_exc = RuntimeError("something went wrong in the worker")

    mock_result_info = MagicMock()
    mock_result_info.success = False
    mock_result_info.result = raised_exc

    mock_job = AsyncMock()
    mock_job.status = AsyncMock(return_value=JobStatus.complete)
    mock_job.result_info = AsyncMock(return_value=mock_result_info)

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: mock_arq

    with (
        _mock.patch("lyw_core.api.routes.generate.Job", return_value=mock_job),
        TestClient(_app) as c,
    ):
        response = c.get("/lessons/lesson-1/generate/job-failed-runtime")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["job_id"] == "job-failed-runtime"
    assert "error" in body["result"]
    assert "something went wrong in the worker" in body["result"]["error"]


# ---------------------------------------------------------------------------
# OpenAPI schema
# ---------------------------------------------------------------------------


def test_generate_routes_in_openapi_schema(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/lessons/{lesson_id}/generate" in paths
    assert "post" in paths["/lessons/{lesson_id}/generate"]
    assert (
        paths["/lessons/{lesson_id}/generate"]["post"]["operationId"]
        == "generateLesson"
    )
    assert "/lessons/{lesson_id}/generate/{job_id}" in paths
    assert "get" in paths["/lessons/{lesson_id}/generate/{job_id}"]
    assert (
        paths["/lessons/{lesson_id}/generate/{job_id}"]["get"]["operationId"]
        == "getGenerateResult"
    )
