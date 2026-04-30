"""Section quiz orchestrator and Glows/Grows feedback generator.

SectionQuizGenerator calls MCQGenerator per concept and concatenates results.
Items are persisted inside MCQGenerator.generate() — this class does not
re-persist. The dao is held for future use (T13).
See docs/plans/phase-2/T9-section-quiz.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import structlog

from lesson_graph.interfaces import ModelClient
from lesson_graph.models import AssessmentItem, ConceptNode, LessonGraph
from lyw_core.assessment.mcq import MCQGenerator
from lyw_core.assessment.prompts.quiz import build_glows_grows_messages
from lyw_core.db import Database
from lyw_core.db.dao import AttemptRecord

_logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class GlowsGrows:
    """Frozen feedback summary after a quiz attempt.

    Not subject to source faithfulness — meta-commentary on learner
    performance, not an educational claim about subject matter.
    """

    glows: str
    grows: str


class SectionQuizGenerator:
    """Orchestrates per-concept MCQ generation and post-quiz Glows/Grows feedback."""

    def __init__(
        self,
        mcq_generator: MCQGenerator,
        model_client: ModelClient,
        dao: Database,
    ) -> None:
        self._mcq_gen = mcq_generator
        self._model = model_client
        self._dao = dao

    async def generate(
        self,
        concepts: list[ConceptNode],
        lesson_graph: LessonGraph,
        *,
        quiz_id: str | None = None,
    ) -> list[AssessmentItem]:
        """Generate MCQ items for every concept in the section.

        The optional ``quiz_id`` is threaded through to every
        ``MCQGenerator.generate`` call so that all items in the quiz share
        a common identifier. Pass ``None`` (default) to preserve the
        pre-T0c-r3 behaviour for quizzes that do not need Glows/Grows lookup.

        Returns the concatenation of all per-concept items (coverage
        enforcement is delegated to the T10 section-quality validators).
        """
        items: list[AssessmentItem] = []
        for concept in concepts:
            concept_items = await self._mcq_gen.generate(
                concept, lesson_graph, quiz_id=quiz_id
            )
            items.extend(concept_items)
        return items

    async def generate_glows_grows(
        self,
        items: list[AssessmentItem],
        attempts: list[AttemptRecord],
    ) -> GlowsGrows:
        """Produce Glows/Grows feedback from quiz items and attempt results."""
        messages = build_glows_grows_messages(items, attempts)
        raw = await self._model.complete(messages)
        return self._parse_glows_grows(raw)

    @staticmethod
    def _parse_glows_grows(raw: str) -> GlowsGrows:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            _logger.warning("glows_grows_parse_failed", reason=f"invalid JSON: {exc}")
            return GlowsGrows(glows="", grows="")

        if not isinstance(data, dict):
            _logger.warning(
                "glows_grows_parse_failed", reason="response was not a JSON object"
            )
            return GlowsGrows(glows="", grows="")

        glows = data.get("glows")
        grows = data.get("grows")
        if not isinstance(glows, str) or not isinstance(grows, str):
            _logger.warning(
                "glows_grows_parse_failed", reason="missing or non-string glows/grows"
            )
            return GlowsGrows(glows="", grows="")

        return GlowsGrows(glows=glows, grows=grows)
