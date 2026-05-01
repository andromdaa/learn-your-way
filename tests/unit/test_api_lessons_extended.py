"""Unit tests for the extended lessons routes added in PR 1."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from lesson_graph import ConceptNode, LessonGraph, SourceSpan
from lesson_graph.models import AssessmentItem
from lyw_core.api.app import create_app, get_arq_redis, get_data_dir, get_db
from lyw_core.db.dao import DerivedAsset, LessonSummary, QuizSummary


@asynccontextmanager
async def _null_lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


def _span(doc_id: str = "doc-1") -> SourceSpan:
    return SourceSpan(
        doc_id=doc_id, page_start=1, page_end=1, char_start=0, char_end=50
    )


def _graph(lesson_id: str = "g1") -> LessonGraph:
    return LessonGraph(
        id=lesson_id,
        source_id="src-1",
        concepts=[
            ConceptNode(
                id="c1",
                title="Concept 1",
                summary="Summary.",
                learning_objective="Understand it.",
                source_spans=[_span()],
                prerequisites=[],
            ),
            ConceptNode(
                id="c2",
                title="Concept 2",
                summary="Summary 2.",
                learning_objective="Understand 2.",
                source_spans=[_span()],
                prerequisites=["c1"],
            ),
        ],
    )


def _item(item_id: str, concept_id: str, quiz_id: str | None = None) -> AssessmentItem:
    return AssessmentItem(
        id=item_id,
        kind="mcq",
        prompt=f"Q for {concept_id}",
        rationale="Because.",
        source_spans=[_span()],
        difficulty="easy",
        concept_id=concept_id,
        correct_answer="A",
        quiz_id=quiz_id,
    )


def _make_client(mock_db: AsyncMock) -> TestClient:
    _app = create_app(lifespan=_null_lifespan)
    _app.dependency_overrides[get_db] = lambda: mock_db
    _app.dependency_overrides[get_arq_redis] = lambda: AsyncMock()
    _app.dependency_overrides[get_data_dir] = lambda: MagicMock()
    return TestClient(_app)


# ---------------------------------------------------------------------------
# GET /lessons
# ---------------------------------------------------------------------------


def test_list_lessons_empty() -> None:
    mock_db = AsyncMock()
    mock_db.list_lessons.return_value = []
    with _make_client(mock_db) as c:
        response = c.get("/lessons")
    assert response.status_code == 200
    assert response.json() == []


def test_list_lessons_returns_summaries() -> None:
    mock_db = AsyncMock()
    mock_db.list_lessons.return_value = [
        LessonSummary(
            id="g1",
            source_id="src-1",
            concept_count=3,
            created_at="2026-01-01T00:00:00",
        ),
    ]
    with _make_client(mock_db) as c:
        response = c.get("/lessons")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "g1"
    assert body[0]["concept_count"] == 3


# ---------------------------------------------------------------------------
# GET /lessons/{lesson_id}/concepts/{concept_id}
# ---------------------------------------------------------------------------


def test_get_concept_node_found() -> None:
    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = _graph()
    with _make_client(mock_db) as c:
        response = c.get("/lessons/g1/concepts/c1")
    assert response.status_code == 200
    assert response.json()["id"] == "c1"


def test_get_concept_node_lesson_not_found() -> None:
    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = None
    with _make_client(mock_db) as c:
        response = c.get("/lessons/no-lesson/concepts/c1")
    assert response.status_code == 404
    assert "Lesson" in response.json()["detail"]


def test_get_concept_node_concept_not_found() -> None:
    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = _graph()
    with _make_client(mock_db) as c:
        response = c.get("/lessons/g1/concepts/no-concept")
    assert response.status_code == 404
    assert "Concept" in response.json()["detail"]


# ---------------------------------------------------------------------------
# GET /lessons/{lesson_id}/items
# ---------------------------------------------------------------------------


def test_list_lesson_items_all_concepts() -> None:
    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = _graph()
    mock_db.get_items_by_concept.side_effect = [
        [_item("i1", "c1")],
        [_item("i2", "c2")],
    ]
    with _make_client(mock_db) as c:
        response = c.get("/lessons/g1/items")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_lesson_items_filter_by_concept() -> None:
    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = _graph()
    mock_db.get_items_by_concept.return_value = [_item("i1", "c1")]
    with _make_client(mock_db) as c:
        response = c.get("/lessons/g1/items?concept_id=c1")
    assert response.status_code == 200
    assert len(response.json()) == 1
    mock_db.get_items_by_concept.assert_called_once_with("c1")


def test_list_lesson_items_filter_by_quiz() -> None:
    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = _graph()
    mock_db.get_items_by_quiz_id.return_value = [
        _item("i1", "c1", quiz_id="quiz-1"),
        _item("i2", "c2", quiz_id="quiz-1"),
    ]
    with _make_client(mock_db) as c:
        response = c.get("/lessons/g1/items?quiz_id=quiz-1")
    assert response.status_code == 200
    assert len(response.json()) == 2
    mock_db.get_items_by_quiz_id.assert_called_once_with("quiz-1")


def test_list_lesson_items_lesson_not_found() -> None:
    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = None
    with _make_client(mock_db) as c:
        response = c.get("/lessons/no-lesson/items")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /lessons/{lesson_id}/assets
# ---------------------------------------------------------------------------


def test_list_lesson_assets_returns_filtered_list() -> None:
    asset = DerivedAsset(
        id="a1",
        lesson_id="g1",
        concept_id="c1",
        kind="mnemonic",
        profile_id="p1",
        file_path="/f/a.txt",
        created_at="2026-01-01T00:00:00",
    )
    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = _graph()
    mock_db.list_derived_assets.return_value = [asset]
    with _make_client(mock_db) as c:
        response = c.get("/lessons/g1/assets?kind=mnemonic&profile_id=p1")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "a1"
    mock_db.list_derived_assets.assert_called_once_with(
        "g1", concept_id=None, kind="mnemonic", profile_id="p1"
    )


def test_list_lesson_assets_lesson_not_found() -> None:
    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = None
    with _make_client(mock_db) as c:
        response = c.get("/lessons/no-lesson/assets")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /lessons/{lesson_id}/quizzes
# ---------------------------------------------------------------------------


def test_list_lesson_quizzes_returns_summaries() -> None:
    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = _graph()
    mock_db.list_quizzes.return_value = [QuizSummary(quiz_id="quiz-1", item_count=4)]
    with _make_client(mock_db) as c:
        response = c.get("/lessons/g1/quizzes")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["quiz_id"] == "quiz-1"
    assert body[0]["item_count"] == 4


def test_list_lesson_quizzes_empty() -> None:
    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = _graph()
    mock_db.list_quizzes.return_value = []
    with _make_client(mock_db) as c:
        response = c.get("/lessons/g1/quizzes")
    assert response.status_code == 200
    assert response.json() == []


def test_list_lesson_quizzes_lesson_not_found() -> None:
    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = None
    with _make_client(mock_db) as c:
        response = c.get("/lessons/no-lesson/quizzes")
    assert response.status_code == 404
