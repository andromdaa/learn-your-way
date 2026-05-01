"""Unit tests for GET /healthz."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from lyw_core.api.app import create_app, get_arq_redis, get_db
from lyw_core.api.routes.health import ServiceHealth
from lyw_core.healthcheck import ServiceStatus


@asynccontextmanager
async def _null_lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


def _make_client(mock_db: AsyncMock) -> TestClient:
    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()
    return TestClient(_app)


def _healthy(name: str) -> ServiceStatus:
    return ServiceStatus(name=name, healthy=True, detail="ok")


def _unhealthy(name: str) -> ServiceStatus:
    return ServiceStatus(name=name, healthy=False, detail="connection refused")


def test_healthz_all_healthy() -> None:
    mock_db = AsyncMock()
    mock_db._conn = AsyncMock()
    mock_db._conn.execute = AsyncMock()

    with (
        patch("lyw_core.api.routes.health.ping_redis", return_value=_healthy("redis")),
        patch("lyw_core.api.routes.health.ping_qdrant", return_value=_healthy("qdrant")),
        patch("lyw_core.api.routes.health._ping_ollama", return_value=ServiceHealth(ok=True)),
    ):
        with _make_client(mock_db) as c:
            response = c.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["redis"]["ok"] is True
    assert body["qdrant"]["ok"] is True
    assert body["db"]["ok"] is True
    assert body["ollama"]["ok"] is True


def test_healthz_redis_down_returns_200_with_ok_false() -> None:
    mock_db = AsyncMock()
    mock_db._conn = AsyncMock()
    mock_db._conn.execute = AsyncMock()

    with (
        patch("lyw_core.api.routes.health.ping_redis", return_value=_unhealthy("redis")),
        patch("lyw_core.api.routes.health.ping_qdrant", return_value=_healthy("qdrant")),
        patch("lyw_core.api.routes.health._ping_ollama", return_value=ServiceHealth(ok=True)),
    ):
        with _make_client(mock_db) as c:
            response = c.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["redis"]["ok"] is False
    assert body["redis"]["detail"] == "connection refused"


def test_healthz_db_failure_still_returns_200() -> None:
    mock_db = AsyncMock()
    mock_db._conn = AsyncMock()
    mock_db._conn.execute = AsyncMock(side_effect=Exception("disk full"))

    with (
        patch("lyw_core.api.routes.health.ping_redis", return_value=_healthy("redis")),
        patch("lyw_core.api.routes.health.ping_qdrant", return_value=_healthy("qdrant")),
        patch("lyw_core.api.routes.health._ping_ollama", return_value=ServiceHealth(ok=True)),
    ):
        with _make_client(mock_db) as c:
            response = c.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["db"]["ok"] is False
    assert "disk full" in body["db"]["detail"]


# ---------------------------------------------------------------------------
# _ping_ollama unit tests
# ---------------------------------------------------------------------------


async def test_ping_ollama_success() -> None:
    from lyw_core.api.routes.health import ServiceHealth, _ping_ollama

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await _ping_ollama("http://localhost:11434")

    assert result == ServiceHealth(ok=True)


async def test_ping_ollama_failure() -> None:
    from lyw_core.api.routes.health import ServiceHealth, _ping_ollama

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await _ping_ollama("http://localhost:11434")

    assert result == ServiceHealth(ok=False, detail="connection refused")
