"""Unit tests for the extended profiles CRUD routes added in PR 1."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from lyw_core.api.app import create_app, get_arq_redis, get_data_dir, get_db
from lyw_core.db.dao import AttemptRecord
from lyw_core.profiles.models import LearnerProfile


@asynccontextmanager
async def _null_lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


def _profile(profile_id: str = "p1") -> LearnerProfile:
    return LearnerProfile(
        id=profile_id, grade_level="8", interests=["math"], goals=["pass exam"]
    )


def _attempt(attempt_id: str = "a1", profile_id: str = "p1") -> AttemptRecord:
    return AttemptRecord(
        id=attempt_id,
        profile_id=profile_id,
        item_id="item-1",
        response="A",
        correct=True,
        attempted_at="2026-01-01T00:00:00",
    )


def _make_client(mock_db: AsyncMock) -> TestClient:
    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()
    return TestClient(_app)


# ---------------------------------------------------------------------------
# GET /profiles
# ---------------------------------------------------------------------------


def test_list_profiles_empty() -> None:
    mock_db = AsyncMock()
    mock_db.list_profiles.return_value = []
    with _make_client(mock_db) as c:
        response = c.get("/profiles")
    assert response.status_code == 200
    assert response.json() == []


def test_list_profiles_returns_all() -> None:
    mock_db = AsyncMock()
    mock_db.list_profiles.return_value = [_profile("p1"), _profile("p2")]
    with _make_client(mock_db) as c:
        response = c.get("/profiles")
    assert response.status_code == 200
    assert len(response.json()) == 2


# ---------------------------------------------------------------------------
# GET /profiles/{profile_id}
# ---------------------------------------------------------------------------


def test_get_profile_found() -> None:
    mock_db = AsyncMock()
    mock_db.get_profile.return_value = _profile("p1")
    with _make_client(mock_db) as c:
        response = c.get("/profiles/p1")
    assert response.status_code == 200
    assert response.json()["id"] == "p1"


def test_get_profile_not_found_returns_404() -> None:
    mock_db = AsyncMock()
    mock_db.get_profile.return_value = None
    with _make_client(mock_db) as c:
        response = c.get("/profiles/no-such-profile")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PUT /profiles/{profile_id}
# ---------------------------------------------------------------------------


def test_update_profile_returns_updated_profile() -> None:
    mock_db = AsyncMock()
    mock_db.get_profile.return_value = _profile("p1")
    mock_db.add_profile.return_value = None
    with _make_client(mock_db) as c:
        response = c.put(
            "/profiles/p1",
            json={"grade_level": "9", "interests": ["science"], "goals": ["A grade"]},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "p1"
    assert body["grade_level"] == "9"
    assert body["interests"] == ["science"]


def test_update_profile_not_found_returns_404() -> None:
    mock_db = AsyncMock()
    mock_db.get_profile.return_value = None
    with _make_client(mock_db) as c:
        response = c.put(
            "/profiles/no-such-profile",
            json={"grade_level": "9"},
        )
    assert response.status_code == 404


def test_update_profile_empty_grade_level_returns_422() -> None:
    mock_db = AsyncMock()
    mock_db.get_profile.return_value = _profile("p1")
    with _make_client(mock_db) as c:
        response = c.put(
            "/profiles/p1",
            json={"grade_level": "   "},
        )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /profiles/{profile_id}
# ---------------------------------------------------------------------------


def test_delete_profile_returns_204() -> None:
    mock_db = AsyncMock()
    mock_db.delete_profile.return_value = True
    with _make_client(mock_db) as c:
        response = c.delete("/profiles/p1")
    assert response.status_code == 204
    mock_db.delete_profile.assert_called_once_with("p1")


def test_delete_profile_not_found_returns_404() -> None:
    mock_db = AsyncMock()
    mock_db.delete_profile.return_value = False
    with _make_client(mock_db) as c:
        response = c.delete("/profiles/no-such-profile")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /profiles/{profile_id}/attempts
# ---------------------------------------------------------------------------


def test_list_profile_attempts_returns_attempts() -> None:
    mock_db = AsyncMock()
    mock_db.get_profile.return_value = _profile("p1")
    mock_db.get_profile_attempts.return_value = [
        _attempt("a1", "p1"),
        _attempt("a2", "p1"),
    ]
    with _make_client(mock_db) as c:
        response = c.get("/profiles/p1/attempts")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["profile_id"] == "p1"


def test_list_profile_attempts_empty() -> None:
    mock_db = AsyncMock()
    mock_db.get_profile.return_value = _profile("p1")
    mock_db.get_profile_attempts.return_value = []
    with _make_client(mock_db) as c:
        response = c.get("/profiles/p1/attempts")
    assert response.status_code == 200
    assert response.json() == []


def test_list_profile_attempts_profile_not_found() -> None:
    mock_db = AsyncMock()
    mock_db.get_profile.return_value = None
    with _make_client(mock_db) as c:
        response = c.get("/profiles/no-such-profile/attempts")
    assert response.status_code == 404
