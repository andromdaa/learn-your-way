"""POST /attempts and POST /recommendations/next — assessment API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lesson_graph.models import SourceSpan
from lyw_core.api.app import get_db
from lyw_core.assessment.gap import GapDetector
from lyw_core.db.dao import Database

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class AttemptRequest(BaseModel):
    profile_id: str
    item_id: str
    response: str


class AttemptFeedback(BaseModel):
    correct: bool
    rationale: str
    source_spans: list[SourceSpan]
    suggested_next_concept_id: str | None = None


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

    if item.correct_answer is None:
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

    return AttemptFeedback(
        correct=correct,
        rationale=rationale,
        source_spans=item.source_spans,
        suggested_next_concept_id=None,
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
