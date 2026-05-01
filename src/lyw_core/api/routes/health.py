"""GET /healthz — aggregate service health check."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from lyw_core.api.app import get_db
from lyw_core.db.dao import Database
from lyw_core.healthcheck import ping_qdrant, ping_redis
from lyw_core.settings import Settings

router = APIRouter()


class ServiceHealth(BaseModel):
    ok: bool
    detail: str | None = None


class HealthResponse(BaseModel):
    redis: ServiceHealth
    qdrant: ServiceHealth
    db: ServiceHealth
    ollama: ServiceHealth
    model_name: str


async def _ping_db(db: Database) -> ServiceHealth:
    try:
        await db._conn.execute("SELECT 1")
        return ServiceHealth(ok=True)
    except Exception as exc:
        return ServiceHealth(ok=False, detail=str(exc))


async def _ping_ollama(base_url: str) -> ServiceHealth:
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url}/api/version")
            resp.raise_for_status()
        return ServiceHealth(ok=True)
    except Exception as exc:
        return ServiceHealth(ok=False, detail=str(exc))


@router.get("/healthz", response_model=HealthResponse, operation_id="getHealth")
async def healthz(
    db: Annotated[Database, Depends(get_db)],
) -> HealthResponse:
    cfg = Settings()
    redis_raw, qdrant_raw, db_health, ollama_health = await asyncio.gather(
        ping_redis(cfg.redis_url),
        ping_qdrant(cfg.qdrant_url),
        _ping_db(db),
        _ping_ollama(cfg.ollama_base_url),
    )
    return HealthResponse(
        redis=ServiceHealth(
            ok=redis_raw.healthy,
            detail=None if redis_raw.healthy else redis_raw.detail,
        ),
        qdrant=ServiceHealth(
            ok=qdrant_raw.healthy,
            detail=None if qdrant_raw.healthy else qdrant_raw.detail,
        ),
        db=db_health,
        ollama=ollama_health,
        model_name=cfg.model_name,
    )
