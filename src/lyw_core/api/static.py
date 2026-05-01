"""SPA static file serving — mounts web/dist/ and provides SPA fallback.

Only active when ``web/dist/index.html`` exists (i.e., after ``pnpm build``).
In dev mode the Vite dev server handles the frontend; FastAPI only serves the
JSON API.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

_WEB_DIST = Path(__file__).resolve().parents[3] / "web" / "dist"


def mount_spa(app: FastAPI) -> None:
    """Conditionally mount the built SPA and register the fallback route.

    Call this *after* all API routers have been registered so that the SPA
    fallback is truly last and cannot shadow API paths.
    """
    index = _WEB_DIST / "index.html"
    if not index.exists():
        return

    app.mount("/assets", StaticFiles(directory=str(_WEB_DIST / "assets")), name="spa-assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def _spa_fallback(path: str) -> FileResponse:
        return FileResponse(str(index))
