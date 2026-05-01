"""End-to-end flow: profile creation → quiz attempts → Glows/Grows → recommendation.

Uses in-memory SQLite; mocks only the LLM call inside generate_glows_grows.
No Qdrant, Redis, or Ollama required.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from lesson_graph import ConceptNode, LessonGraph, SourceSpan
from lesson_graph.models import AssessmentItem
from lyw_core.api.app import create_app, get_arq_redis, get_data_dir, get_db
from lyw_core.db.dao import Database
from lyw_core.profiles.models import LearnerProfile

pytestmark = pytest.mark.integration

_LESSON_ID = "lesson-flow-test"
_SOURCE_ID = "doc-flow-test"
_QUIZ_ID = "quiz-flow-001"
_PROFILE_ID = "profile-flow-001"


def _span() -> SourceSpan:
    return SourceSpan(doc_id=_SOURCE_ID, page_start=1, page_end=1, char_start=0, char_end=50)


def _graph() -> LessonGraph:
    return LessonGraph(
        id=_LESSON_ID,
        source_id=_SOURCE_ID,
        concepts=[
            ConceptNode(
                id="c-flow-1",
                title="Concept Alpha",
                summary="Alpha summary.",
                learning_objective="Understand Alpha.",
                source_spans=[_span()],
                prerequisites=[],
            ),
            ConceptNode(
                id="c-flow-2",
                title="Concept Beta",
                summary="Beta summary.",
                learning_objective="Understand Beta.",
                source_spans=[_span()],
                prerequisites=["c-flow-1"],
            ),
        ],
    )


def _item(item_id: str, concept_id: str, correct_answer: str) -> AssessmentItem:
    return AssessmentItem(
        id=item_id,
        kind="mcq",
        prompt=f"Question about {concept_id}?",
        correct_answer=correct_answer,
        rationale="Because.",
        difficulty="medium",
        options=["A", "B", correct_answer],
        source_spans=[_span()],
        concept_id=concept_id,
        quiz_id=_QUIZ_ID,
    )


@asynccontextmanager
async def _null_lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


@pytest.fixture
async def db(tmp_path: Path) -> Database:
    database = await Database.connect(str(tmp_path / "full_flow.db"))
    await database.add_source(_SOURCE_ID, str(tmp_path / "doc.pdf"), "abc123")
    await database.upsert_lesson_graph(_graph())
    profile = LearnerProfile(
        id=_PROFILE_ID,
        grade_level="10",
        interests=["science"],
        goals=["pass exam"],
    )
    await database.add_profile(profile)
    items = [
        _item("item-flow-1", "c-flow-1", "C"),
        _item("item-flow-2", "c-flow-2", "C"),
    ]
    for item in items:
        await database.add_assessment_item(item)
    return database


@pytest.fixture
def app(db: Database) -> FastAPI:
    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: db
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()
    return _app


@pytest.mark.integration
async def test_profile_creation_and_retrieval(app: FastAPI) -> None:
    """Profile created during fixture setup is retrievable via GET /profiles/{id}."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/profiles/{_PROFILE_ID}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == _PROFILE_ID
    assert body["grade_level"] == "10"


@pytest.mark.integration
async def test_lesson_and_items_readable(app: FastAPI) -> None:
    """Lesson graph and quiz items are queryable after DB setup."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        graph_resp = await client.get(f"/lessons/{_LESSON_ID}")
        items_resp = await client.get(f"/lessons/{_LESSON_ID}/quiz/{_QUIZ_ID}")
    assert graph_resp.status_code == 200
    assert len(graph_resp.json()["concepts"]) == 2
    assert items_resp.status_code == 200
    assert len(items_resp.json()) == 2


@pytest.mark.integration
async def test_record_attempts_deferred_glows_grows(app: FastAPI) -> None:
    """Attempts recorded with defer_glows_grows=true return correct feedback without LLM call."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.post(
            "/attempts",
            json={
                "profile_id": _PROFILE_ID,
                "item_id": "item-flow-1",
                "response": "C",
                "defer_glows_grows": True,
            },
        )
        r2 = await client.post(
            "/attempts",
            json={
                "profile_id": _PROFILE_ID,
                "item_id": "item-flow-2",
                "response": "A",
                "defer_glows_grows": True,
            },
        )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["correct"] is True
    assert r2.json()["correct"] is False


@pytest.mark.integration
async def test_glows_grows_after_attempts(db: Database, app: FastAPI) -> None:
    """POST /quizzes/{id}/glows-grows returns glows/grows string pair from LLM."""
    # Record attempts first
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for item_id, response in [("item-flow-1", "C"), ("item-flow-2", "A")]:
            await client.post(
                "/attempts",
                json={
                    "profile_id": _PROFILE_ID,
                    "item_id": item_id,
                    "response": response,
                    "defer_glows_grows": True,
                },
            )

    mock_model = AsyncMock()
    mock_model.complete = AsyncMock(
        return_value='{"glows": "Strong on Alpha.", "grows": "Review Beta concepts."}'
    )

    with (
        patch("lyw_core.api.routes.quizzes.Settings") as mock_settings_cls,
        patch("lyw_core.api.routes.quizzes.OllamaModelClient", return_value=mock_model),
    ):
        mock_settings_cls.return_value.ollama_base_url = "http://localhost:11434"
        mock_settings_cls.return_value.model_name = "gemma3:4b"
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/quizzes/{_QUIZ_ID}/glows-grows",
                json={"profile_id": _PROFILE_ID},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert "glows" in body
    assert "grows" in body


@pytest.mark.integration
async def test_next_recommendation_after_quiz(db: Database, app: FastAPI) -> None:
    """POST /recommendations/next returns a concept ID after quiz attempts are recorded."""
    # Record attempts first
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for item_id, response in [("item-flow-1", "C"), ("item-flow-2", "A")]:
            await client.post(
                "/attempts",
                json={
                    "profile_id": _PROFILE_ID,
                    "item_id": item_id,
                    "response": response,
                    "defer_glows_grows": True,
                },
            )
        resp = await client.post(
            "/recommendations/next",
            json={"profile_id": _PROFILE_ID, "lesson_id": _LESSON_ID},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "next_concept_id" in body


@pytest.mark.integration
async def test_attempts_by_quiz_after_submission(db: Database, app: FastAPI) -> None:
    """GET /attempts/by-quiz returns all submitted attempts for the quiz."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for item_id, response in [("item-flow-1", "C"), ("item-flow-2", "C")]:
            await client.post(
                "/attempts",
                json={
                    "profile_id": _PROFILE_ID,
                    "item_id": item_id,
                    "response": response,
                    "defer_glows_grows": True,
                },
            )
        resp = await client.get(
            "/attempts/by-quiz",
            params={"quiz_id": _QUIZ_ID, "profile_id": _PROFILE_ID},
        )
    assert resp.status_code == 200
    records = resp.json()
    assert len(records) == 2
    assert all(r["profile_id"] == _PROFILE_ID for r in records)
