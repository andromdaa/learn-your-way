"""lyw_web ASGI entrypoint.

Composes lyw_core's API with the browser test harness UI.

Run with: uvicorn lyw_web.app:app --reload
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from lyw_core.api.app import _default_lifespan
from lyw_core.api.app import create_app as _create_core_app
from lyw_core.settings import Settings
from lyw_web.queries import WebQueries
from lyw_web.routes import router as ui_router

_WEB_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def _web_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with _default_lifespan(app):
        cfg = Settings()
        app.state.web_queries = await WebQueries.connect(str(cfg.db_path))
        try:
            yield
        finally:
            await app.state.web_queries.close()


def create_app(
    lifespan: Callable[..., Any] = _web_lifespan,
) -> FastAPI:
    app = _create_core_app(lifespan=lifespan)
    app.state.templates = Jinja2Templates(directory=str(_WEB_DIR / "templates"))
    app.mount(
        "/static",
        StaticFiles(directory=str(_WEB_DIR / "static")),
        name="static",
    )
    app.include_router(ui_router)
    return app


app = create_app()
