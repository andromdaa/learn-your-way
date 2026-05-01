"""HTML routes for the browser test harness."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

from lyw_core.api.app import get_db
from lyw_core.db.dao import Database
from lyw_web.deps import get_web_queries
from lyw_web.queries import WebQueries

router = APIRouter()


def _templates(request: Request) -> Jinja2Templates:
    t: Jinja2Templates = request.app.state.templates
    return t


@router.get("/", include_in_schema=False)
async def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/ui", status_code=302)


@router.get("/ui", include_in_schema=False)
async def ui_index(
    request: Request,
    db: Annotated[Database, Depends(get_db)],
    wq: Annotated[WebQueries, Depends(get_web_queries)],
) -> Response:
    lessons = await wq.list_lessons()
    profiles = await db.list_profiles()
    return _templates(request).TemplateResponse(
        request=request,
        name="index.html",
        context={"lessons": lessons, "profiles": profiles},
    )


@router.get("/ui/lesson/{lesson_id}", include_in_schema=False)
async def ui_lesson(
    lesson_id: str,
    request: Request,
    db: Annotated[Database, Depends(get_db)],
    wq: Annotated[WebQueries, Depends(get_web_queries)],
) -> Response:
    graph = await db.get_lesson_graph(lesson_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    profiles = await db.list_profiles()
    assets = await wq.list_derived_assets(lesson_id)
    return _templates(request).TemplateResponse(
        request=request,
        name="lesson.html",
        context={
            "graph": graph,
            "profiles": profiles,
            "assets": assets,
            "lesson_scoped_id": "__lesson__",
            "lesson_scoped_kinds": ["mind_map", "timeline", "slides"],
            "concept_scoped_kinds": ["relevel", "replace", "mnemonic"],
        },
    )
