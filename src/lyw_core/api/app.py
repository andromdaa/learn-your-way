"""FastAPI application factory and shared dependencies."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

import arq
from arq.connections import ArqRedis, RedisSettings
from fastapi import FastAPI, Request

from lyw_core.db.dao import Database
from lyw_core.settings import Settings
from lyw_core.storage.fs import DataDir


@asynccontextmanager
async def _default_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    cfg = Settings()
    app.state.db = await Database.connect(str(cfg.db_path))
    app.state.data_dir = DataDir(cfg.data_dir)
    app.state.data_dir.bootstrap()
    app.state.arq_redis = await arq.create_pool(RedisSettings.from_dsn(cfg.redis_url))
    yield
    await app.state.db.close()
    await app.state.arq_redis.close()


def get_db(request: Request) -> Database:
    db: Database = request.app.state.db
    return db


def get_data_dir(request: Request) -> DataDir:
    data_dir: DataDir = request.app.state.data_dir
    return data_dir


def get_arq_redis(request: Request) -> ArqRedis:
    arq_redis: ArqRedis = request.app.state.arq_redis
    return arq_redis


def create_app(
    lifespan: Callable[..., Any] = _default_lifespan,
) -> FastAPI:
    from lyw_core.api.routes.lessons import router as lessons_router
    from lyw_core.api.routes.sources import router as sources_router

    app = FastAPI(
        title="Learn Your Way OSS API",
        version="0.1.0",
        description=(
            "First-party API for the self-hosted Learn Your Way replica. "
            "All generation paths are grounded in source documents and the "
            "canonical lesson graph."
        ),
        lifespan=lifespan,
        servers=[{"url": "http://localhost:8000/v1"}],
    )
    app.include_router(sources_router)
    app.include_router(lessons_router)
    return app


app = create_app()
