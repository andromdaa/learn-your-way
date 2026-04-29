"""Integration tests for healthcheck — requires Docker."""

import pytest
from testcontainers.qdrant import QdrantContainer
from testcontainers.redis import RedisContainer

from lyw_core.healthcheck import ServiceStatus, check_all, ping_qdrant, ping_redis


@pytest.mark.integration
async def test_ping_qdrant_live() -> None:
    with QdrantContainer() as qdrant:
        url = f"http://{qdrant.get_container_host_ip()}:{qdrant.get_exposed_port(6333)}"
        result = await ping_qdrant(url)
    assert result == ServiceStatus(name="qdrant", healthy=True, detail="ok")


@pytest.mark.integration
async def test_ping_redis_live() -> None:
    with RedisContainer() as redis_c:
        host = redis_c.get_container_host_ip()
        port = redis_c.get_exposed_port(6379)
        result = await ping_redis(f"redis://{host}:{port}/0")
    assert result == ServiceStatus(name="redis", healthy=True, detail="ok")


@pytest.mark.integration
async def test_check_all_live() -> None:
    with QdrantContainer() as qdrant, RedisContainer() as redis_c:
        qdrant_url = (
            f"http://{qdrant.get_container_host_ip()}:{qdrant.get_exposed_port(6333)}"
        )
        redis_host = redis_c.get_container_host_ip()
        redis_port = redis_c.get_exposed_port(6379)
        redis_url = f"redis://{redis_host}:{redis_port}/0"
        statuses = await check_all(qdrant_url, redis_url)
    assert all(s.healthy for s in statuses)
    assert {s.name for s in statuses} == {"qdrant", "redis"}
