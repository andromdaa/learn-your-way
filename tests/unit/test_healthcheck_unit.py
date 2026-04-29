"""Unit tests for lyw_core.healthcheck — no Docker required."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lyw_core.healthcheck import ServiceStatus, check_all, ping_qdrant, ping_redis


@pytest.mark.asyncio
async def test_ping_qdrant_success() -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    with patch("lyw_core.healthcheck.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client
        result = await ping_qdrant("http://localhost:6333")
    assert result == ServiceStatus(name="qdrant", healthy=True, detail="ok")


@pytest.mark.asyncio
async def test_ping_qdrant_failure() -> None:
    import httpx

    with patch("lyw_core.healthcheck.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client
        result = await ping_qdrant("http://localhost:6333")
    assert result.name == "qdrant"
    assert result.healthy is False
    assert "refused" in result.detail


@pytest.mark.asyncio
async def test_ping_redis_success() -> None:
    with patch("lyw_core.healthcheck.redis.asyncio.from_url") as mock_from_url:
        mock_conn = AsyncMock()
        mock_conn.ping = AsyncMock(return_value=True)
        mock_conn.aclose = AsyncMock()
        mock_from_url.return_value = mock_conn
        result = await ping_redis("redis://localhost:6379/0")
    assert result == ServiceStatus(name="redis", healthy=True, detail="ok")


@pytest.mark.asyncio
async def test_ping_redis_failure() -> None:
    import redis.exceptions

    with patch("lyw_core.healthcheck.redis.asyncio.from_url") as mock_from_url:
        mock_conn = AsyncMock()
        mock_conn.ping = AsyncMock(
            side_effect=redis.exceptions.ConnectionError("refused")
        )
        mock_conn.aclose = AsyncMock()
        mock_from_url.return_value = mock_conn
        result = await ping_redis("redis://localhost:6379/0")
    assert result.name == "redis"
    assert result.healthy is False
    assert "refused" in result.detail


@pytest.mark.asyncio
async def test_check_all_all_healthy() -> None:
    with (
        patch(
            "lyw_core.healthcheck.ping_qdrant",
            new=AsyncMock(
                return_value=ServiceStatus(name="qdrant", healthy=True, detail="ok")
            ),
        ),
        patch(
            "lyw_core.healthcheck.ping_redis",
            new=AsyncMock(
                return_value=ServiceStatus(name="redis", healthy=True, detail="ok")
            ),
        ),
    ):
        statuses = await check_all("http://localhost:6333", "redis://localhost:6379/0")
    assert all(s.healthy for s in statuses)


@pytest.mark.asyncio
async def test_check_all_one_unhealthy() -> None:
    with (
        patch(
            "lyw_core.healthcheck.ping_qdrant",
            new=AsyncMock(
                return_value=ServiceStatus(
                    name="qdrant", healthy=False, detail="refused"
                )
            ),
        ),
        patch(
            "lyw_core.healthcheck.ping_redis",
            new=AsyncMock(
                return_value=ServiceStatus(name="redis", healthy=True, detail="ok")
            ),
        ),
    ):
        statuses = await check_all("http://localhost:6333", "redis://localhost:6379/0")
    names = {s.name: s.healthy for s in statuses}
    assert names["qdrant"] is False
    assert names["redis"] is True
