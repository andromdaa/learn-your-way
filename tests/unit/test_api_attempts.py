"""Unit tests for POST /v1/attempts — Glows-Grows wiring (T0c-r4).

These tests focus on the new behaviour: quiz-item attempts return non-null
glows/grows; non-quiz attempts return null; manual-eval fallback preserved.
All DB and model-client calls are mocked; no real DB or Ollama required.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from lesson_graph import ConceptNode, LessonGraph, SourceSpan
from lesson_graph.models import AssessmentItem
from lyw_core.api.app import create_app, get_arq_redis, get_data_dir, get_db
from lyw_core.assessment.quiz import GlowsGrows


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


def _mcq_item(
    *,
    quiz_id: str | None = None,
    correct_answer: str | None = "Paris",
) -> AssessmentItem:
    return AssessmentItem(
        id="item-1",
        kind="mcq",
        prompt="What is the capital of France?",
        rationale="Paris is the capital.",
        source_spans=[_span()],
        difficulty="easy",
        concept_id="c1",
        correct_answer=correct_answer,
        quiz_id=quiz_id,
    )


def _make_app(mock_db: AsyncMock) -> FastAPI:
    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()
    return _app


# ---------------------------------------------------------------------------
# Non-quiz item: glows/grows must be null
# ---------------------------------------------------------------------------


def test_post_attempts_non_quiz_item_has_null_glows_grows() -> None:
    """When quiz_id is None, glows and grows must be null in the response."""
    item = _mcq_item(quiz_id=None)
    mock_db = AsyncMock()
    mock_db.get_item_by_id.return_value = item
    mock_db.record_attempt.return_value = None
    mock_db.get_lesson_id_by_concept_id.return_value = "lesson-1"
    mock_db.get_lesson_graph.return_value = _graph()
    mock_db.get_profile_attempts.return_value = []

    with TestClient(_make_app(mock_db)) as c:
        response = c.post(
            "/attempts",
            json={"profile_id": "p1", "item_id": "item-1", "response": "Paris"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["glows"] is None
    assert body["grows"] is None


# ---------------------------------------------------------------------------
# Quiz item: glows/grows must be populated
# ---------------------------------------------------------------------------


def test_post_attempts_quiz_item_returns_glows_grows() -> None:
    """When quiz_id is set and model returns valid JSON, glows/grows are non-null."""
    item = _mcq_item(quiz_id="quiz-abc")
    sibling_item = _mcq_item(quiz_id="quiz-abc")
    mock_db = AsyncMock()
    mock_db.get_item_by_id.return_value = item
    mock_db.record_attempt.return_value = None
    mock_db.get_lesson_id_by_concept_id.return_value = "lesson-1"
    mock_db.get_lesson_graph.return_value = _graph()
    mock_db.get_profile_attempts.return_value = []
    mock_db.get_items_by_quiz_id.return_value = [sibling_item]
    mock_db.get_attempts_by_quiz_id.return_value = []

    fake_glows_grows = GlowsGrows(
        glows="You correctly identified Paris.",
        grows="Review the history of France.",
    )

    with (
        patch(
            "lyw_core.api.routes.attempts.SectionQuizGenerator.generate_glows_grows",
            new=AsyncMock(return_value=fake_glows_grows),
        ),
        TestClient(_make_app(mock_db)) as c,
    ):
        response = c.post(
            "/attempts",
            json={"profile_id": "p1", "item_id": "item-1", "response": "Paris"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["glows"] == "You correctly identified Paris."
    assert body["grows"] == "Review the history of France."


# ---------------------------------------------------------------------------
# Manual evaluation fallback preserved for non-MCQ items
# ---------------------------------------------------------------------------


def test_post_attempts_manual_eval_returns_null_glows_grows() -> None:
    """Manual-eval items (correct_answer=None) skip Glows-Grows; null in response."""
    item = _mcq_item(quiz_id="quiz-abc", correct_answer=None)
    mock_db = AsyncMock()
    mock_db.get_item_by_id.return_value = item
    mock_db.record_attempt.return_value = None
    mock_db.get_lesson_id_by_concept_id.return_value = "lesson-1"
    mock_db.get_lesson_graph.return_value = _graph()
    mock_db.get_profile_attempts.return_value = []

    with TestClient(_make_app(mock_db)) as c:
        response = c.post(
            "/attempts",
            json={"profile_id": "p1", "item_id": "item-1", "response": "some answer"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is False
    assert body["rationale"] == "Manual evaluation required"
    assert body["glows"] is None
    assert body["grows"] is None


# ---------------------------------------------------------------------------
# AttemptFeedback schema: glows/grows fields exist and default to None
# ---------------------------------------------------------------------------


def test_attempt_feedback_schema_has_glows_grows_fields() -> None:
    """AttemptFeedback Pydantic model has optional glows/grows defaulting to None."""
    from lyw_core.api.routes.attempts import AttemptFeedback

    feedback = AttemptFeedback(
        correct=True,
        rationale="test",
        source_spans=[_span()],
    )
    assert feedback.glows is None
    assert feedback.grows is None


def test_attempt_feedback_schema_accepts_glows_grows_strings() -> None:
    """AttemptFeedback accepts string glows/grows values."""
    from lyw_core.api.routes.attempts import AttemptFeedback

    feedback = AttemptFeedback(
        correct=True,
        rationale="test",
        source_spans=[_span()],
        glows="Well done on the quiz.",
        grows="Review topic X.",
    )
    assert feedback.glows == "Well done on the quiz."
    assert feedback.grows == "Review topic X."


# ---------------------------------------------------------------------------
# defer_glows_grows flag: skips inline G/G generation
# ---------------------------------------------------------------------------


def test_post_attempts_defer_glows_grows_returns_null_glows_grows() -> None:
    """When defer_glows_grows=True on a quiz item, glows/grows must be null."""
    item = _mcq_item(quiz_id="quiz-abc")
    mock_db = AsyncMock()
    mock_db.get_item_by_id.return_value = item
    mock_db.record_attempt.return_value = None
    mock_db.get_lesson_id_by_concept_id.return_value = "lesson-1"
    mock_db.get_lesson_graph.return_value = _graph()
    mock_db.get_profile_attempts.return_value = []

    with TestClient(_make_app(mock_db)) as c:
        response = c.post(
            "/attempts",
            json={
                "profile_id": "p1",
                "item_id": "item-1",
                "response": "Paris",
                "defer_glows_grows": True,
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["glows"] is None
    assert body["grows"] is None
