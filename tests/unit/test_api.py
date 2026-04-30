"""Unit tests for the FastAPI endpoints — no real DB, Redis, or queue."""

from __future__ import annotations

import io
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lesson_graph import ConceptNode, LessonGraph, SourceSpan
from lesson_graph.models import AssessmentItem
from lyw_core.api.app import create_app, get_arq_redis, get_data_dir, get_db


@asynccontextmanager
async def _null_lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


def _span() -> SourceSpan:
    return SourceSpan(
        doc_id="doc-1", page_start=1, page_end=1, char_start=0, char_end=50
    )


def _graph() -> LessonGraph:
    return LessonGraph(
        id="lesson_doc-1",
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


@pytest.fixture()
def client() -> Iterator[TestClient]:
    mock_db = AsyncMock()
    mock_db.get_source.return_value = None
    mock_db.get_lesson_graph.return_value = _graph()

    mock_data_dir = MagicMock()
    mock_data_dir.write_source.return_value = Path("/tmp/test.pdf")

    mock_arq = AsyncMock()

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_data_dir] = lambda: mock_data_dir
    _app.dependency_overrides[get_arq_redis] = lambda: mock_arq

    with TestClient(_app) as c:
        yield c


def test_post_sources_returns_202(client: TestClient) -> None:
    pdf_bytes = b"%PDF-1.4 minimal"
    response = client.post(
        "/sources",
        files={"file": ("sample.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 202


def test_post_sources_response_schema(client: TestClient) -> None:
    pdf_bytes = b"%PDF-1.4 minimal"
    response = client.post(
        "/sources",
        files={"file": ("sample.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    body = response.json()
    assert "id" in body
    assert "title" in body
    assert body["status"] == "parsing"


def test_get_lesson_returns_graph(client: TestClient) -> None:
    response = client.get("/lessons/lesson_doc-1")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "lesson_doc-1"
    assert body["source_id"] == "doc-1"
    spans = body["concepts"][0]["source_spans"]
    assert spans[0]["char_start"] < spans[0]["char_end"]


def test_get_lesson_404() -> None:
    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = None

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()

    with TestClient(_app) as c:
        response = c.get("/lessons/nonexistent")
    assert response.status_code == 404


def test_post_sources_skips_add_when_source_exists() -> None:
    """Branch: source already registered — add_source must not be called."""
    mock_db = AsyncMock()
    mock_db.get_source.return_value = {"doc_id": "existing"}

    mock_data_dir = MagicMock()
    mock_data_dir.write_source.return_value = Path("/tmp/test.pdf")

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_data_dir] = lambda: mock_data_dir
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()

    with TestClient(_app) as c:
        c.post(
            "/sources",
            files={"file": ("dup.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        )
    mock_db.add_source.assert_not_awaited()


def test_dep_functions_read_from_app_state() -> None:
    """get_db / get_data_dir / get_arq_redis proxy request.app.state."""
    from lyw_core.api.app import _default_lifespan  # noqa: F401 — imported for coverage

    mock_db = MagicMock()
    mock_data_dir = MagicMock()
    mock_arq = MagicMock()

    _app = create_app(lifespan=_null_lifespan)
    _app.state.db = mock_db
    _app.state.data_dir = mock_data_dir
    _app.state.arq_redis = mock_arq

    request = MagicMock()
    request.app = _app

    assert get_db(request) is mock_db
    assert get_data_dir(request) is mock_data_dir
    assert get_arq_redis(request) is mock_arq


async def test_default_lifespan_connects_and_closes() -> None:
    """_default_lifespan wires DB, DataDir, and arq pool onto app.state."""
    from lyw_core.api.app import _default_lifespan

    mock_db = AsyncMock()
    mock_arq = AsyncMock()
    mock_data_dir_inst = MagicMock()

    with (
        patch("lyw_core.api.app.Database.connect", return_value=mock_db),
        patch("lyw_core.api.app.arq.create_pool", return_value=mock_arq),
        patch("lyw_core.api.app.DataDir", return_value=mock_data_dir_inst),
    ):
        _app = FastAPI()
        async with _default_lifespan(_app):
            assert _app.state.db is mock_db
            assert _app.state.arq_redis is mock_arq
            assert _app.state.data_dir is mock_data_dir_inst

        mock_db.close.assert_awaited_once()
        mock_arq.close.assert_awaited_once()


def test_openapi_routes_present(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/sources" in paths
    assert "post" in paths["/sources"]
    assert paths["/sources"]["post"]["operationId"] == "createSource"
    assert "/lessons/{lesson_id}" in paths
    assert "get" in paths["/lessons/{lesson_id}"]
    assert paths["/lessons/{lesson_id}"]["get"]["operationId"] == "getLesson"
    servers = schema.get("servers", [])
    assert any("v1" in s["url"] for s in servers)


# ---------------------------------------------------------------------------
# POST /profiles
# ---------------------------------------------------------------------------


def test_post_profiles_returns_200(client: TestClient) -> None:
    response = client.post(
        "/profiles",
        json={"grade_level": "8", "interests": ["football"], "goals": ["pass exam"]},
    )
    assert response.status_code == 200


def test_post_profiles_returns_saved_profile(client: TestClient) -> None:
    response = client.post(
        "/profiles",
        json={"grade_level": "9", "interests": ["chess"], "goals": ["improve ranking"]},
    )
    body = response.json()
    assert body["grade_level"] == "9"
    assert body["interests"] == ["chess"]
    assert body["goals"] == ["improve ranking"]
    assert "id" in body


def test_post_profiles_missing_grade_level_returns_422(client: TestClient) -> None:
    response = client.post(
        "/profiles",
        json={"interests": ["chess"], "goals": ["improve"]},
    )
    assert response.status_code == 422


def test_post_profiles_empty_grade_level_returns_422(client: TestClient) -> None:
    response = client.post(
        "/profiles",
        json={"grade_level": "", "interests": [], "goals": []},
    )
    assert response.status_code == 422


def test_post_profiles_duplicate_upserts_cleanly(client: TestClient) -> None:
    payload = {"grade_level": "7", "interests": ["art"], "goals": ["learn basics"]}
    r1 = client.post("/profiles", json=payload)
    r2 = client.post("/profiles", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200


def test_post_profiles_in_openapi_schema(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert "/profiles" in schema["paths"]
    assert "post" in schema["paths"]["/profiles"]


# ---------------------------------------------------------------------------
# POST /attempts
# ---------------------------------------------------------------------------


def _mcq_item(correct_answer: str | None = "Paris") -> AssessmentItem:
    return AssessmentItem(
        id="item-1",
        kind="mcq",
        prompt="What is the capital of France?",
        rationale="Paris is the capital.",
        source_spans=[_span()],
        difficulty="easy",
        concept_id="c1",
        correct_answer=correct_answer,
    )


def test_post_attempts_returns_200_correct(client: TestClient) -> None:
    item = _mcq_item("Paris")
    client.app.dependency_overrides[get_db].return_value = None  # type: ignore[attr-defined]
    # Use a dedicated mock for this test
    mock_db = AsyncMock()
    mock_db.get_item_by_id.return_value = item
    mock_db.record_attempt.return_value = None
    mock_db.get_lesson_graph.return_value = _graph()

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()

    with TestClient(_app) as c:
        response = c.post(
            "/attempts",
            json={"profile_id": "p1", "item_id": "item-1", "response": "Paris"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is True
    assert body["rationale"] == "Paris is the capital."
    assert "source_spans" in body
    assert body["suggested_next_concept_id"] is None


def test_post_attempts_returns_200_incorrect(client: TestClient) -> None:
    item = _mcq_item("Paris")
    mock_db = AsyncMock()
    mock_db.get_item_by_id.return_value = item
    mock_db.record_attempt.return_value = None
    mock_db.get_lesson_graph.return_value = _graph()

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()

    with TestClient(_app) as c:
        response = c.post(
            "/attempts",
            json={"profile_id": "p1", "item_id": "item-1", "response": "Lyon"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is False


def test_post_attempts_returns_404_unknown_item(client: TestClient) -> None:
    mock_db = AsyncMock()
    mock_db.get_item_by_id.return_value = None

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()

    with TestClient(_app) as c:
        response = c.post(
            "/attempts",
            json={"profile_id": "p1", "item_id": "unknown", "response": "anything"},
        )
    assert response.status_code == 404


def test_post_attempts_null_correct_answer_returns_manual_eval(
    client: TestClient,
) -> None:
    item = _mcq_item(None)
    mock_db = AsyncMock()
    mock_db.get_item_by_id.return_value = item
    mock_db.record_attempt.return_value = None
    mock_db.get_lesson_graph.return_value = _graph()

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()

    with TestClient(_app) as c:
        response = c.post(
            "/attempts",
            json={"profile_id": "p1", "item_id": "item-1", "response": "some answer"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is False
    assert body["rationale"] == "Manual evaluation required"


# ---------------------------------------------------------------------------
# POST /recommendations/next
# ---------------------------------------------------------------------------


def test_post_recommendations_next_returns_concept_id_when_gap_exists() -> None:
    from lyw_core.assessment.gap import GapDetector

    graph = LessonGraph(
        id="lesson_doc-1",
        source_id="doc-1",
        concepts=[
            ConceptNode(
                id="c1",
                title="Concept One",
                summary="Summary.",
                learning_objective="Understand it.",
                source_spans=[_span()],
                prerequisites=["c2"],
            ),
            ConceptNode(
                id="c2",
                title="Concept Two",
                summary="Prereq summary.",
                learning_objective="Learn prereq.",
                source_spans=[_span()],
                prerequisites=[],
            ),
        ],
    )

    prereq_node = graph.concepts[1]

    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = graph

    mock_detector = AsyncMock(spec=GapDetector)
    mock_detector.next_concept.return_value = prereq_node

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()

    with (
        patch(
            "lyw_core.api.routes.attempts.GapDetector",
            return_value=mock_detector,
        ),
        TestClient(_app) as c,
    ):
        response = c.post(
            "/recommendations/next",
            json={"profile_id": "p1", "lesson_id": "lesson_doc-1"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["next_concept_id"] == "c2"
    assert "reason" in body


def test_post_recommendations_next_returns_null_when_no_gap() -> None:
    from lyw_core.assessment.gap import GapDetector

    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = _graph()

    mock_detector = AsyncMock(spec=GapDetector)
    mock_detector.next_concept.return_value = None

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()

    with (
        patch(
            "lyw_core.api.routes.attempts.GapDetector",
            return_value=mock_detector,
        ),
        TestClient(_app) as c,
    ):
        response = c.post(
            "/recommendations/next",
            json={"profile_id": "p1", "lesson_id": "lesson_doc-1"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["next_concept_id"] is None
    assert body["reason"] == "all objectives mastered or no attempts recorded"


def test_post_recommendations_next_lesson_not_found_returns_404() -> None:
    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = None

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()

    with TestClient(_app) as c:
        response = c.post(
            "/recommendations/next",
            json={"profile_id": "p1", "lesson_id": "nonexistent"},
        )
    assert response.status_code == 404
