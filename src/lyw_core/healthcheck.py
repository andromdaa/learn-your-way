"""Async connectivity probes for Qdrant and Redis."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from typing import Any

import httpx
import redis.asyncio
import redis.exceptions

from lyw_core.settings import Settings


@dataclass(frozen=True)
class ServiceStatus:
    name: str
    healthy: bool
    detail: str


async def ping_qdrant(qdrant_url: str) -> ServiceStatus:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{qdrant_url}/readyz")
            resp.raise_for_status()
        return ServiceStatus(name="qdrant", healthy=True, detail="ok")
    except Exception as exc:
        return ServiceStatus(name="qdrant", healthy=False, detail=str(exc))


async def ping_redis(redis_url: str) -> ServiceStatus:
    conn: Any = redis.asyncio.from_url(  # type: ignore[no-untyped-call]
        redis_url, socket_connect_timeout=5
    )
    try:
        await conn.ping()
        return ServiceStatus(name="redis", healthy=True, detail="ok")
    except Exception as exc:
        return ServiceStatus(name="redis", healthy=False, detail=str(exc))
    finally:
        await conn.aclose()


async def check_all(qdrant_url: str, redis_url: str) -> list[ServiceStatus]:
    return list(await asyncio.gather(ping_qdrant(qdrant_url), ping_redis(redis_url)))


async def _main() -> int:
    settings = Settings()
    statuses = await check_all(settings.qdrant_url, settings.redis_url)
    all_healthy = True
    for s in statuses:
        icon = "OK" if s.healthy else "FAIL"
        print(f"[{icon}] {s.name}: {s.detail}")
        if not s.healthy:
            all_healthy = False
    return 0 if all_healthy else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
