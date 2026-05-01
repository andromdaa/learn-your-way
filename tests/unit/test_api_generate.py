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
from lyw_core.worker.result import Failure, Success


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
        json={"concept_id": "c1", "profile_id": "p1", "kind": "relevel"},
    )
    assert response.status_code == 202


def test_post_generate_response_schema(client: TestClient) -> None:
    response = client.post(
        "/lessons/lesson-1/generate",
        json={"concept_id": "c1", "profile_id": "p1", "kind": "relevel"},
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
            json={"concept_id": "c1", "profile_id": "p1", "kind": "relevel"},
        )
    assert response.status_code == 404


def test_post_generate_invalid_kind_returns_422(client: TestClient) -> None:
    response = client.post(
        "/lessons/lesson-1/generate",
        json={"concept_id": "c1", "profile_id": "p1", "kind": "invalid_kind"},
    )
    assert response.status_code == 422


def test_post_generate_all_valid_kinds(client: TestClient) -> None:
    for kind in ("relevel", "replace"):
        response = client.post(
            "/lessons/lesson-1/generate",
            json={"concept_id": "c1", "profile_id": "p1", "kind": kind},
        )
        assert response.status_code == 202, f"kind={kind!r} should be accepted"


def test_post_generate_dropped_kinds_rejected(client: TestClient) -> None:
    """Modality and Phase-2 kinds were removed per ADR-0016 and must be rejected."""
    for kind in ("mind_map", "timeline", "slides", "mnemonic"):
        response = client.post(
            "/lessons/lesson-1/generate",
            json={"concept_id": "c1", "profile_id": "p1", "kind": kind},
        )
        assert response.status_code == 422, f"kind={kind!r} should be rejected"


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
            json={"concept_id": "c1", "profile_id": "p1", "kind": "relevel"},
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


def test_get_generate_result_complete_with_typed_success() -> None:
    """A complete job returning Success returns status=complete and result payload."""
    import unittest.mock as _mock

    mock_db = AsyncMock()
    mock_arq = AsyncMock()

    mock_result_info = MagicMock()
    mock_result_info.success = True
    mock_result_info.result = Success(
        payload={"asset_id": "a1", "file_path": "/data/assets/x.txt"}
    )

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


def test_get_generate_result_failed_with_typed_failure_validation() -> None:
    """When the job returned Failure(code=validation_failed), endpoint returns status=failed.

    This test explicitly exercises the custom lyw_core.validators.base.ValidationError
    failure path (not pydantic.ValidationError — those are different classes).
    The job catches the custom ValidationError and converts it to a typed Failure;
    no exception crosses the Arq pickle boundary.
    """
    import unittest.mock as _mock

    mock_db = AsyncMock()
    mock_arq = AsyncMock()

    typed_failure = Failure(
        code="validation_failed",
        message="source faithfulness check failed; span outside concept source range",
        details={"reasons": ["span outside concept source range"]},
    )

    mock_result_info = MagicMock()
    mock_result_info.success = True  # job returned normally — no exception raised
    mock_result_info.result = typed_failure

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
    assert body["result"]["code"] == "validation_failed"
    assert "error" in body["result"]
    assert "faithfulness" in body["result"]["error"]


def test_get_generate_result_failed_with_typed_failure_thin_source() -> None:
    """When the job returned Failure(code=thin_source), endpoint returns status=failed."""
    import unittest.mock as _mock

    mock_db = AsyncMock()
    mock_arq = AsyncMock()

    typed_failure = Failure(
        code="thin_source",
        message="concept 'c1' summary too thin for replace generator: 10 chars, 2 words",
        details={"concept_id": "c1", "char_count": 10, "word_count": 2},
    )

    mock_result_info = MagicMock()
    mock_result_info.success = True
    mock_result_info.result = typed_failure

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
        response = c.get("/lessons/lesson-1/generate/job-thin")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["result"]["code"] == "thin_source"
    assert body["result"]["concept_id"] == "c1"


def test_get_generate_result_failed_with_unexpected_exception() -> None:
    """When the job raised an unexpected exception (info.success=False), endpoint returns status=failed.

    This path covers infrastructure errors (DB down, OOM, etc.) that were not
    wrapped by the job boundary — distinct from typed Failure returns.
    """
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
