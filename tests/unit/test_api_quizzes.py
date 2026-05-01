"""Unit tests for quizzes routes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from lesson_graph.models import AssessmentItem, ConceptNode, LessonGraph, SourceSpan
from lyw_core.api.app import create_app, get_arq_redis, get_db
from lyw_core.assessment.quiz import GlowsGrows
from lyw_core.db.dao import AttemptRecord


@asynccontextmanager
async def _null_lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


def _make_client(mock_db: AsyncMock, mock_arq: AsyncMock | None = None) -> TestClient:
    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: mock_arq or AsyncMock()
    return TestClient(_app)


def _concept(cid: str = "c1") -> ConceptNode:
    return ConceptNode(
        id=cid,
        title="T",
        summary="s",
        learning_objective="lo",
        source_spans=[SourceSpan(doc_id="d", page_start=1, page_end=1, char_start=0, char_end=5)],
    )


def _graph() -> LessonGraph:
    return LessonGraph(id="l1", source_id="doc-1", concepts=[_concept("c1"), _concept("c2")])


def _item(item_id: str = "i1", quiz_id: str | None = "quiz-1") -> AssessmentItem:
    return AssessmentItem(
        id=item_id,
        kind="mcq",
        prompt="Q?",
        rationale="r",
        source_spans=[SourceSpan(doc_id="d", page_start=1, page_end=1, char_start=0, char_end=5)],
        difficulty="easy",
        concept_id="c1",
        correct_answer="A",
        options=["A", "B"],
        quiz_id=quiz_id,
    )


def _attempt(attempt_id: str = "a1") -> AttemptRecord:
    return AttemptRecord(
        id=attempt_id,
        profile_id="p1",
        item_id="i1",
        response="A",
        correct=True,
        attempted_at="2025-01-01T00:00:00",
    )


# ---------------------------------------------------------------------------
# POST /lessons/{lesson_id}/quiz
# ---------------------------------------------------------------------------


def test_generate_quiz_enqueues_job_returns_202() -> None:
    db = AsyncMock()
    db.get_lesson_graph.return_value = _graph()
    arq = AsyncMock()
    mock_job = MagicMock()
    mock_job.job_id = "job-1"
    arq.enqueue_job = AsyncMock(return_value=mock_job)

    with _make_client(db, arq) as c:
        response = c.post("/lessons/l1/quiz", json={"profile_id": "p1"})

    assert response.status_code == 202
    body = response.json()
    assert body["job_id"] == "job-1"
    assert body["status"] == "queued"


def test_generate_quiz_lesson_not_found_returns_404() -> None:
    db = AsyncMock()
    db.get_lesson_graph.return_value = None

    with _make_client(db) as c:
        response = c.post("/lessons/missing/quiz", json={"profile_id": "p1"})

    assert response.status_code == 404


def test_generate_quiz_duplicate_job_returns_409() -> None:
    db = AsyncMock()
    db.get_lesson_graph.return_value = _graph()
    arq = AsyncMock()
    arq.enqueue_job = AsyncMock(return_value=None)

    with _make_client(db, arq) as c:
        response = c.post("/lessons/l1/quiz", json={"profile_id": "p1"})

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# POST /lessons/{lesson_id}/concepts/{concept_id}/mcq
# ---------------------------------------------------------------------------


def test_generate_mcq_enqueues_concept_scope_job() -> None:
    db = AsyncMock()
    db.get_lesson_graph.return_value = _graph()
    arq = AsyncMock()
    mock_job = MagicMock()
    mock_job.job_id = "job-mcq"
    arq.enqueue_job = AsyncMock(return_value=mock_job)

    with _make_client(db, arq) as c:
        response = c.post("/lessons/l1/concepts/c1/mcq", json={"profile_id": "p1"})

    assert response.status_code == 202
    assert response.json()["job_id"] == "job-mcq"
    call_kwargs: dict[str, Any] = arq.enqueue_job.call_args[1]
    assert call_kwargs["scope"] == "concept"
    assert call_kwargs["concept_ids"] == ["c1"]


def test_generate_mcq_concept_not_found_returns_404() -> None:
    db = AsyncMock()
    db.get_lesson_graph.return_value = _graph()

    with _make_client(db) as c:
        response = c.post("/lessons/l1/concepts/missing/mcq", json={"profile_id": "p1"})

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /lessons/{lesson_id}/quiz/{quiz_id}
# ---------------------------------------------------------------------------


def test_get_quiz_returns_items() -> None:
    db = AsyncMock()
    db.get_lesson_graph.return_value = _graph()
    db.get_items_by_quiz_id.return_value = [_item("i1"), _item("i2")]

    with _make_client(db) as c:
        response = c.get("/lessons/l1/quiz/quiz-1")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_quiz_not_found_returns_404() -> None:
    db = AsyncMock()
    db.get_lesson_graph.return_value = _graph()
    db.get_items_by_quiz_id.return_value = []

    with _make_client(db) as c:
        response = c.get("/lessons/l1/quiz/missing")

    assert response.status_code == 404


def test_get_quiz_lesson_not_found_returns_404() -> None:
    db = AsyncMock()
    db.get_lesson_graph.return_value = None

    with _make_client(db) as c:
        response = c.get("/lessons/missing/quiz/q1")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /attempts/by-quiz
# ---------------------------------------------------------------------------


def test_get_attempts_by_quiz_returns_list() -> None:
    db = AsyncMock()
    db.get_attempts_by_quiz_id.return_value = [_attempt("a1"), _attempt("a2")]

    with _make_client(db) as c:
        response = c.get("/attempts/by-quiz?quiz_id=quiz-1&profile_id=p1")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_attempts_by_quiz_empty_returns_empty_list() -> None:
    db = AsyncMock()
    db.get_attempts_by_quiz_id.return_value = []

    with _make_client(db) as c:
        response = c.get("/attempts/by-quiz?quiz_id=quiz-1&profile_id=p1")

    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# POST /quizzes/{quiz_id}/glows-grows
# ---------------------------------------------------------------------------


def test_generate_glows_grows_returns_feedback() -> None:
    db = AsyncMock()
    db.get_items_by_quiz_id.return_value = [_item()]
    db.get_attempts_by_quiz_id.return_value = [_attempt()]

    with patch("lyw_core.api.routes.quizzes.Settings"):
        with patch("lyw_core.api.routes.quizzes.OllamaModelClient"):
            with patch("lyw_core.api.routes.quizzes.MCQGenerator"):
                with patch("lyw_core.api.routes.quizzes.SectionQuizGenerator") as mock_sg:
                    mock_sg.return_value.generate_glows_grows = AsyncMock(
                        return_value=GlowsGrows(glows="Great job!", grows="Review X")
                    )
                    with _make_client(db) as c:
                        response = c.post(
                            "/quizzes/quiz-1/glows-grows", json={"profile_id": "p1"}
                        )

    assert response.status_code == 200
    body = response.json()
    assert body["glows"] == "Great job!"
    assert body["grows"] == "Review X"


def test_generate_glows_grows_quiz_not_found_returns_404() -> None:
    db = AsyncMock()
    db.get_items_by_quiz_id.return_value = []

    with _make_client(db) as c:
        response = c.post("/quizzes/missing/glows-grows", json={"profile_id": "p1"})

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /lessons/{lesson_id}/bulk-generate
# ---------------------------------------------------------------------------


def test_bulk_generate_enqueues_job_returns_202() -> None:
    db = AsyncMock()
    db.get_lesson_graph.return_value = _graph()
    arq = AsyncMock()
    mock_job = MagicMock()
    mock_job.job_id = "bulk-job-1"
    arq.enqueue_job = AsyncMock(return_value=mock_job)

    with _make_client(db, arq) as c:
        response = c.post(
            "/lessons/l1/bulk-generate",
            json={"profile_id": "p1", "kinds": ["relevel", "replace"]},
        )

    assert response.status_code == 202
    assert response.json()["job_id"] == "bulk-job-1"


def test_bulk_generate_lesson_not_found_returns_404() -> None:
    db = AsyncMock()
    db.get_lesson_graph.return_value = None

    with _make_client(db) as c:
        response = c.post(
            "/lessons/missing/bulk-generate",
            json={"profile_id": "p1", "kinds": ["relevel"]},
        )

    assert response.status_code == 404
