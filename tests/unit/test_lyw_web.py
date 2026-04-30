"""Smoke tests for lyw_web HTML routes."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lesson_graph import ConceptNode, LessonGraph, SourceSpan
from lyw_core.api.app import get_arq_redis, get_data_dir, get_db
from lyw_core.profiles.models import LearnerProfile
from lyw_web.app import create_app
from lyw_web.deps import get_web_queries
from lyw_web.queries import AssetRow, LessonSummary, WebQueries


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


def _profile() -> LearnerProfile:
    return LearnerProfile(
        id="prof-1",
        grade_level="8",
        interests=["football"],
        goals=["understand gravity"],
    )


def _lesson_summary() -> LessonSummary:
    return LessonSummary(
        id="lesson_doc-1",
        source_id="doc-1",
        concept_count=1,
        created_at="2026-01-01T00:00:00",
    )


def _asset_row() -> AssetRow:
    return AssetRow(
        id="asset-1",
        lesson_id="lesson_doc-1",
        concept_id="__lesson__",
        kind="mind_map",
        profile_id="prof-1",
        file_path="/data/assets/ab/abc.mmd",
        created_at="2026-01-01T01:00:00",
    )


@pytest.fixture()
def client_empty() -> Iterator[TestClient]:
    mock_db = AsyncMock()
    mock_db.list_profiles.return_value = []
    mock_db.get_lesson_graph.return_value = None

    mock_wq = MagicMock(spec=WebQueries)
    mock_wq.list_lessons = AsyncMock(return_value=[])
    mock_wq.list_derived_assets = AsyncMock(return_value=[])

    mock_data_dir = MagicMock()
    mock_arq = AsyncMock()

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_data_dir] = lambda: mock_data_dir
    _app.dependency_overrides[get_arq_redis] = lambda: mock_arq
    _app.dependency_overrides[get_web_queries] = lambda: mock_wq

    with TestClient(_app, follow_redirects=False) as c:
        yield c


@pytest.fixture()
def client_populated() -> Iterator[TestClient]:
    mock_db = AsyncMock()
    mock_db.list_profiles.return_value = [_profile()]
    mock_db.get_lesson_graph.return_value = _graph()

    mock_wq = MagicMock(spec=WebQueries)
    mock_wq.list_lessons = AsyncMock(return_value=[_lesson_summary()])
    mock_wq.list_derived_assets = AsyncMock(return_value=[_asset_row()])

    mock_data_dir = MagicMock()
    mock_arq = AsyncMock()

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_data_dir] = lambda: mock_data_dir
    _app.dependency_overrides[get_arq_redis] = lambda: mock_arq
    _app.dependency_overrides[get_web_queries] = lambda: mock_wq

    with TestClient(_app, follow_redirects=False) as c:
        yield c


# ---------------------------------------------------------------------------
# Root redirect
# ---------------------------------------------------------------------------


def test_root_redirects_to_ui(client_empty: TestClient) -> None:
    r = client_empty.get("/")
    assert r.status_code == 302
    assert r.headers["location"] == "/ui"


# ---------------------------------------------------------------------------
# GET /ui — index
# ---------------------------------------------------------------------------


def test_ui_index_returns_200(client_empty: TestClient) -> None:
    r = client_empty.get("/ui")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_ui_index_empty_state(client_empty: TestClient) -> None:
    r = client_empty.get("/ui")
    assert "No lessons yet" in r.text
    assert "No profiles yet" in r.text


def test_ui_index_populated(client_populated: TestClient) -> None:
    r = client_populated.get("/ui")
    assert r.status_code == 200
    assert "lesson_doc-1" in r.text
    assert "football" in r.text  # profile interests


# ---------------------------------------------------------------------------
# GET /ui/lesson/{lesson_id}
# ---------------------------------------------------------------------------


def test_ui_lesson_missing_returns_404(client_empty: TestClient) -> None:
    r = client_empty.get("/ui/lesson/no-such-lesson")
    assert r.status_code == 404


def test_ui_lesson_present_returns_200(client_populated: TestClient) -> None:
    r = client_populated.get("/ui/lesson/lesson_doc-1")
    assert r.status_code == 200
    assert "Concept One" in r.text


def test_ui_lesson_shows_asset(client_populated: TestClient) -> None:
    r = client_populated.get("/ui/lesson/lesson_doc-1")
    assert "mind_map" in r.text
    assert "asset-1" in r.text


# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------


def test_static_css_served(client_empty: TestClient) -> None:
    r = client_empty.get("/static/styles.css")
    assert r.status_code == 200
