"""Unit tests for GET /sources, GET /sources/{doc_id}, GET /sources/{doc_id}/file,
and GET /sources/{doc_id}/excerpt."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lyw_core.api.app import (
    create_app,
    get_arq_redis,
    get_data_dir,
    get_db,
    get_parsed_doc_cache,
)
from lyw_core.db.dao import SourceRow
from lyw_core.parser.models import ParsedDocument


@asynccontextmanager
async def _null_lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


def _source_row(
    doc_id: str = "doc-1",
    path: str = "/data/sources/doc.pdf",
    sha256: str = "abc123",
    created_at: str = "2026-01-01T00:00:00",
    lesson_id: str | None = None,
) -> SourceRow:
    return SourceRow(
        doc_id=doc_id,
        path=path,
        sha256=sha256,
        created_at=created_at,
        lesson_id=lesson_id,
    )


@pytest.fixture()
def client() -> Iterator[TestClient]:
    mock_db = AsyncMock()
    mock_arq = AsyncMock()
    mock_data_dir = MagicMock()

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: mock_arq
    _app.dependency_overrides[get_data_dir] = lambda: mock_data_dir

    with TestClient(_app) as c:
        c.extra = {"db": mock_db}  # type: ignore[attr-defined]
        yield c


# ---------------------------------------------------------------------------
# GET /sources
# ---------------------------------------------------------------------------


def test_list_sources_empty() -> None:
    mock_db = AsyncMock()
    mock_db.list_sources.return_value = []

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()

    with TestClient(_app) as c:
        response = c.get("/sources")
    assert response.status_code == 200
    assert response.json() == []


def test_list_sources_returns_rows() -> None:
    rows = [
        _source_row("d1", lesson_id=None),
        _source_row("d2", lesson_id="lesson_d2"),
    ]
    mock_db = AsyncMock()
    mock_db.list_sources.return_value = rows

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()

    with TestClient(_app) as c:
        response = c.get("/sources")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["doc_id"] == "d1"
    assert body[0]["lesson_id"] is None
    assert body[1]["lesson_id"] == "lesson_d2"


# ---------------------------------------------------------------------------
# GET /sources/{doc_id}
# ---------------------------------------------------------------------------


def test_get_source_found() -> None:
    row = _source_row("doc-1", lesson_id="lesson_doc-1")
    mock_db = AsyncMock()
    mock_db.get_source_row.return_value = row

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()

    with TestClient(_app) as c:
        response = c.get("/sources/doc-1")
    assert response.status_code == 200
    body = response.json()
    assert body["doc_id"] == "doc-1"
    assert body["lesson_id"] == "lesson_doc-1"


def test_get_source_not_found_returns_404() -> None:
    mock_db = AsyncMock()
    mock_db.get_source_row.return_value = None

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()

    with TestClient(_app) as c:
        response = c.get("/sources/no-such-id")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /sources/{doc_id}/file
# ---------------------------------------------------------------------------


def test_get_source_file_returns_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 minimal")

    mock_db = AsyncMock()
    mock_db.get_source.return_value = {"path": str(pdf_path), "doc_id": "doc-1"}

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()

    with TestClient(_app) as c:
        response = c.get("/sources/doc-1/file")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")


def test_get_source_file_source_not_found_returns_404() -> None:
    mock_db = AsyncMock()
    mock_db.get_source.return_value = None

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()

    with TestClient(_app) as c:
        response = c.get("/sources/no-such-id/file")
    assert response.status_code == 404


def test_get_source_file_missing_from_disk_returns_404(tmp_path: Path) -> None:
    mock_db = AsyncMock()
    mock_db.get_source.return_value = {
        "path": str(tmp_path / "gone.pdf"),
        "doc_id": "doc-1",
    }

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()

    with TestClient(_app) as c:
        response = c.get("/sources/doc-1/file")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /sources/{doc_id}/excerpt
# ---------------------------------------------------------------------------


def _parsed_doc(text: str = "Hello world this is a test document.") -> ParsedDocument:
    return ParsedDocument(
        source_path="/tmp/doc.pdf", text=text, blocks=[], page_count=1
    )


def test_get_excerpt_returns_window_from_cache() -> None:
    doc = _parsed_doc("A" * 50 + "SPAN" + "B" * 50)
    mock_db = AsyncMock()

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()
    _app.dependency_overrides[get_parsed_doc_cache] = lambda: {"doc-1": doc}

    with TestClient(_app) as c:
        response = c.get(
            "/sources/doc-1/excerpt",
            params={"char_start": 50, "char_end": 54, "radius": 10},
        )
    assert response.status_code == 200
    body = response.json()
    assert "SPAN" in body["text"]
    assert body["doc_id"] == "doc-1"
    assert body["char_start"] == 50
    assert body["char_end"] == 54
    assert body["window_start"] == 40


def test_get_excerpt_whole_doc_when_radius_exceeds_bounds() -> None:
    text = "short text"
    doc = _parsed_doc(text)
    mock_db = AsyncMock()

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()
    _app.dependency_overrides[get_parsed_doc_cache] = lambda: {"doc-1": doc}

    with TestClient(_app) as c:
        response = c.get(
            "/sources/doc-1/excerpt",
            params={"char_start": 0, "char_end": 5, "radius": 200},
        )
    assert response.status_code == 200
    assert response.json()["text"] == text
    assert response.json()["window_start"] == 0


def test_get_excerpt_source_not_found_returns_404() -> None:
    mock_db = AsyncMock()
    mock_db.get_source.return_value = None

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()
    _app.dependency_overrides[get_parsed_doc_cache] = lambda: {}

    with TestClient(_app) as c:
        response = c.get(
            "/sources/no-such-doc/excerpt",
            params={"char_start": 0, "char_end": 10},
        )
    assert response.status_code == 404


def test_get_excerpt_file_missing_from_disk_returns_404(tmp_path: Path) -> None:
    mock_db = AsyncMock()
    mock_db.get_source.return_value = {
        "path": str(tmp_path / "gone.pdf"),
        "doc_id": "doc-1",
    }

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()
    _app.dependency_overrides[get_parsed_doc_cache] = lambda: {}

    with TestClient(_app) as c:
        response = c.get(
            "/sources/doc-1/excerpt",
            params={"char_start": 0, "char_end": 10},
        )
    assert response.status_code == 404
