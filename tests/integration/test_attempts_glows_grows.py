"""Integration test for Glows-Grows wiring in POST /v1/attempts (T0c-r4).

Uses a real in-memory SQLite database (Database.connect(":memory:")) and mocks
only the model-client call inside generate_glows_grows. No Qdrant or Redis
required; no network calls.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from lesson_graph import ConceptNode, LessonGraph, SourceSpan
from lesson_graph.models import AssessmentItem
from lyw_core.api.app import create_app, get_arq_redis, get_data_dir, get_db
from lyw_core.db.dao import Database
from lyw_core.profiles.models import LearnerProfile


@asynccontextmanager
async def _null_lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


def _span() -> SourceSpan:
    return SourceSpan(
        doc_id="doc-1", page_start=1, page_end=1, char_start=0, char_end=50
    )


def _graph() -> LessonGraph:
    return LessonGraph(
        id="lesson-1",
        source_id="doc-1",
        concepts=[
            ConceptNode(
                id="c1",
                title="Concept One",
                summary="Summary.",
                learning_objective="Understand it.",
                source_spans=[_span()],
                prerequisites=[],
            )
        ],
    )


def _mcq_item(*, quiz_id: str | None) -> AssessmentItem:
    return AssessmentItem(
        id="item-1",
        kind="mcq",
        prompt="What is the capital of France?",
        rationale="Paris is the capital.",
        source_spans=[_span()],
        difficulty="easy",
        concept_id="c1",
        correct_answer="Paris",
        quiz_id=quiz_id,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_quiz_attempt_returns_glows_grows_via_real_db() -> None:
    """Full handler path: real SQLite, mocked model, quiz item -> glows/grows populated."""
    db = await Database.connect(":memory:")
    await db.add_source("doc-1", "/data/doc.pdf", "sha256-test")
    await db.upsert_lesson_graph(_graph())
    await db.add_profile(
        LearnerProfile(id="p1", grade_level="8", interests=[], goals=[])
    )

    item = _mcq_item(quiz_id="quiz-xyz")
    await db.add_assessment_item(item)

    fake_model_response = json.dumps(
        {"glows": "Great job identifying Paris!", "grows": "Review European capitals."}
    )

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: db
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()

    with patch(
        "lyw_core.api.routes.attempts.OllamaModelClient.complete",
        new=AsyncMock(return_value=fake_model_response),
    ):
        transport = ASGITransport(app=_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/attempts",
                json={"profile_id": "p1", "item_id": "item-1", "response": "Paris"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is True
    assert body["glows"] == "Great job identifying Paris!"
    assert body["grows"] == "Review European capitals."

    await db.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_non_quiz_attempt_returns_null_glows_grows_via_real_db() -> None:
    """Full handler path: real SQLite, non-quiz item -> glows/grows null."""
    db = await Database.connect(":memory:")
    await db.add_source("doc-1", "/data/doc.pdf", "sha256-test")
    await db.upsert_lesson_graph(_graph())
    await db.add_profile(
        LearnerProfile(id="p1", grade_level="8", interests=[], goals=[])
    )

    item = _mcq_item(quiz_id=None)
    await db.add_assessment_item(item)

    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: db
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()

    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/attempts",
            json={"profile_id": "p1", "item_id": "item-1", "response": "Paris"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is True
    assert body["glows"] is None
    assert body["grows"] is None

    await db.close()
