"""FastAPI dependencies for lyw_web routes."""

from __future__ import annotations

from fastapi import Request

from lyw_web.queries import WebQueries


def get_web_queries(request: Request) -> WebQueries:
    wq: WebQueries = request.app.state.web_queries
    return wq
