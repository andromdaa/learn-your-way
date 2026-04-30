"""Unit tests for GET /v1/assets/{asset_id} — derived asset retrieval."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lyw_core.api.app import create_app, get_data_dir, get_db
from lyw_core.db.dao import DerivedAsset


@asynccontextmanager
async def _null_lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


def _make_asset(
    asset_id: str = "asset-1",
    file_path: str = "/data/assets/ab/abc.json",
    kind: str = "slides",
) -> DerivedAsset:
    return DerivedAsset(
        id=asset_id,
        lesson_id="lesson-1",
        concept_id="__lesson__",
        kind=kind,
        profile_id="profile-1",
        file_path=file_path,
        created_at="2026-04-30T00:00:00",
    )


@pytest.fixture()
def client_with_asset(tmp_path: Path) -> Iterator[TestClient]:
    """Client where the DAO returns a known asset and the file exists."""
    asset_path = tmp_path / "ab" / "abc.json"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_text('{"slides": [], "based_on_concepts": ["c1"]}')

    asset = _make_asset(file_path=str(asset_path))

    mock_db = AsyncMock()
    mock_db.get_derived_asset_by_id.return_value = asset

    mock_data_dir = MagicMock()

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_data_dir] = lambda: mock_data_dir

    with TestClient(_app) as c:
        yield c


@pytest.fixture()
def client_asset_not_found() -> Iterator[TestClient]:
    """Client where the DAO returns None (asset not found)."""
    mock_db = AsyncMock()
    mock_db.get_derived_asset_by_id.return_value = None

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()

    with TestClient(_app) as c:
        yield c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_get_asset_returns_file_content(
    client_with_asset: TestClient, tmp_path: Path
) -> None:
    """GET /v1/assets/{asset_id} returns the file content for a known asset."""
    response = client_with_asset.get("/v1/assets/asset-1")
    assert response.status_code == 200
    body = response.json()
    assert "slides" in body


def test_get_asset_not_found_returns_404(
    client_asset_not_found: TestClient,
) -> None:
    """GET /v1/assets/{asset_id} returns 404 for an unknown asset_id."""
    response = client_asset_not_found.get("/v1/assets/no-such-asset")
    assert response.status_code == 404


def test_get_asset_file_missing_returns_404(tmp_path: Path) -> None:
    """Returns 404 when DAO row exists but file has been deleted."""
    asset = _make_asset(file_path=str(tmp_path / "missing.json"))

    mock_db = AsyncMock()
    mock_db.get_derived_asset_by_id.return_value = asset

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()

    with TestClient(_app) as c:
        response = c.get("/v1/assets/asset-1")
    assert response.status_code == 404


def test_get_mmd_asset_returns_text_content(tmp_path: Path) -> None:
    """GET /v1/assets/{asset_id} for a .mmd file returns the Mermaid text."""
    mmd_path = tmp_path / "mindmap.mmd"
    mmd_path.write_text("flowchart TD\n    c1[\"Root\"]\n")

    asset = _make_asset(asset_id="asset-mmd", file_path=str(mmd_path), kind="mind_map")

    mock_db = AsyncMock()
    mock_db.get_derived_asset_by_id.return_value = asset

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()

    with TestClient(_app) as c:
        response = c.get("/v1/assets/asset-mmd")
    assert response.status_code == 200
    assert "flowchart" in response.text
