"""FastAPI application factory and shared dependencies."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

import arq
from arq.connections import ArqRedis, RedisSettings
from fastapi import FastAPI, Request

from lyw_core.db.dao import Database
from lyw_core.parser.models import ParsedDocument
from lyw_core.settings import Settings
from lyw_core.storage.fs import DataDir

_PARSED_DOC_CACHE_SIZE = 16


@asynccontextmanager
async def _default_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    cfg = Settings()
    app.state.db = await Database.connect(str(cfg.db_path))
    app.state.data_dir = DataDir(cfg.data_dir)
    app.state.data_dir.bootstrap()
    app.state.arq_redis = await arq.create_pool(RedisSettings.from_dsn(cfg.redis_url))
    app.state.parsed_doc_cache = {}
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


def get_parsed_doc_cache(request: Request) -> dict[str, ParsedDocument]:
    cache: dict[str, ParsedDocument] = request.app.state.parsed_doc_cache
    return cache


def create_app(
    lifespan: Callable[..., Any] = _default_lifespan,
) -> FastAPI:
    from lyw_core.api.routes.attempts import router as attempts_router
    from lyw_core.api.routes.generate import router as generate_router
    from lyw_core.api.routes.health import router as health_router
    from lyw_core.api.routes.jobs import router as jobs_router
    from lyw_core.api.routes.lessons import router as lessons_router
    from lyw_core.api.routes.profiles import router as profiles_router
    from lyw_core.api.routes.quizzes import router as quizzes_router
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
    app.include_router(profiles_router)
    app.include_router(attempts_router)
    app.include_router(generate_router)
    app.include_router(quizzes_router)
    app.include_router(jobs_router)
    app.include_router(health_router)

    from lyw_core.api.static import mount_spa

    mount_spa(app)
    return app


app = create_app()
