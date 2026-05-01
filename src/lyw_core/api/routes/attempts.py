"""POST /attempts and POST /recommendations/next — assessment API."""

from __future__ import annotations

import dataclasses
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lesson_graph.models import SourceSpan
from lyw_core.api.app import get_db
from lyw_core.assessment.gap import GapDetector
from lyw_core.assessment.mcq import MCQGenerator
from lyw_core.assessment.quiz import SectionQuizGenerator
from lyw_core.clients.ollama import OllamaModelClient
from lyw_core.db.dao import Database
from lyw_core.settings import Settings

_logger = structlog.get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class AttemptRequest(BaseModel):
    profile_id: str
    item_id: str
    response: str
    defer_glows_grows: bool = False


class AttemptFeedback(BaseModel):
    correct: bool
    rationale: str
    source_spans: list[SourceSpan]
    suggested_next_concept_id: str | None = None
    glows: str | None = None
    grows: str | None = None


class RecommendationRequest(BaseModel):
    profile_id: str
    lesson_id: str


class RecommendationResponse(BaseModel):
    next_concept_id: str | None
    reason: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/attempts",
    response_model=AttemptFeedback,
    operation_id="recordAttempt",
)
async def record_attempt(
    body: AttemptRequest,
    db: Annotated[Database, Depends(get_db)],
) -> AttemptFeedback:
    """Evaluate and persist a learner's attempt at an assessment item.

    Returns 404 if the item_id is not found.
    For items without a correct_answer (non-MCQ), returns correct=False and
    rationale="Manual evaluation required".
    """
    item = await db.get_item_by_id(body.item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Assessment item not found")

    is_manual_eval = item.correct_answer is None
    if is_manual_eval:
        correct = False
        rationale = "Manual evaluation required"
    else:
        correct = body.response == item.correct_answer
        rationale = item.rationale

    await db.record_attempt(
        profile_id=body.profile_id,
        item_id=body.item_id,
        response=body.response,
        correct=correct,
    )

    suggested_next_concept_id: str | None = None
    lesson_id = await db.get_lesson_id_by_concept_id(item.concept_id)
    if lesson_id is not None:
        graph = await db.get_lesson_graph(lesson_id)
        if graph is not None:
            detector = GapDetector()
            next_node = await detector.next_concept(
                profile_id=body.profile_id,
                lesson_graph=graph,
                dao=db,
            )
            if next_node is not None:
                suggested_next_concept_id = next_node.id

    # Glows-Grows: only for quiz items with a correct_answer (auto-evaluable).
    glows: str | None = None
    grows: str | None = None
    if item.quiz_id is not None and not is_manual_eval and not body.defer_glows_grows:
        try:
            settings = Settings()
            model_client = OllamaModelClient(
                base_url=settings.ollama_base_url,
                model=settings.model_name,
            )
            mcq_gen = MCQGenerator(model_client=model_client, validators=[], dao=db)
            quiz_gen = SectionQuizGenerator(
                mcq_generator=mcq_gen, model_client=model_client, dao=db
            )
            sibling_items = await db.get_items_by_quiz_id(item.quiz_id)
            sibling_attempts = await db.get_attempts_by_quiz_id(
                item.quiz_id, body.profile_id
            )
            feedback = await quiz_gen.generate_glows_grows(
                sibling_items, sibling_attempts
            )
            gg = dataclasses.asdict(feedback)
            glows = gg["glows"]
            grows = gg["grows"]
        except Exception:
            _logger.warning(
                "glows_grows_failed",
                quiz_id=item.quiz_id,
                item_id=item.id,
                exc_info=True,
            )

    return AttemptFeedback(
        correct=correct,
        rationale=rationale,
        source_spans=item.source_spans,
        suggested_next_concept_id=suggested_next_concept_id,
        glows=glows,
        grows=grows,
    )


@router.post(
    "/recommendations/next",
    response_model=RecommendationResponse,
    operation_id="getNextRecommendation",
)
async def get_next_recommendation(
    body: RecommendationRequest,
    db: Annotated[Database, Depends(get_db)],
) -> RecommendationResponse:
    """Return the next concept to revisit based on the learner's gap analysis.

    Returns 404 if the lesson_id is not found.
    Returns next_concept_id=null when no gap is detected.
    """
    graph = await db.get_lesson_graph(body.lesson_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="Lesson not found")

    detector = GapDetector()
    next_node = await detector.next_concept(
        profile_id=body.profile_id,
        lesson_graph=graph,
        dao=db,
    )

    if next_node is None:
        return RecommendationResponse(
            next_concept_id=None,
            reason="all objectives mastered or no attempts recorded",
        )

    return RecommendationResponse(
        next_concept_id=next_node.id,
        reason=f"Unmastered prerequisite for concept '{next_node.title}'",
    )
