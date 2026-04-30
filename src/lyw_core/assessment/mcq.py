"""Embedded MCQ generator: produces 1-3 multiple-choice items per concept.

Returns only items that pass every supplied validator. Items where the
model omits correct_answer or bloom_level are discarded. Accepted items
are persisted via the DAO before being returned. See
docs/plans/phase-2/T8-mcq-generator.md.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from typing import Literal

import structlog
from pydantic import BaseModel, ValidationError

from lesson_graph.interfaces import ModelClient
from lesson_graph.models import AssessmentItem, ConceptNode, LessonGraph
from lyw_core.assessment.prompts.mcq import build_mcq_messages
from lyw_core.db import Database
from lyw_core.validators.base import Validator
from lyw_core.validators.faithfulness import ItemValidationPayload

_logger = structlog.get_logger(__name__)

_BloomLevel = Literal[
    "remember", "understand", "apply", "analyze", "evaluate", "create"
]
_Difficulty = Literal["easy", "medium", "hard"]


class _ModelMCQ(BaseModel):
    """Schema for one element of the model's JSON-array response."""

    prompt: str
    options: list[str]
    correct_answer: str
    rationale: str
    bloom_level: _BloomLevel
    difficulty: _Difficulty


class MCQGenerator:
    """Generates 1-3 MCQs per concept; persists items that pass all validators."""

    def __init__(
        self,
        model_client: ModelClient,
        validators: Sequence[Validator[ItemValidationPayload]],
        dao: Database,
    ) -> None:
        self._model = model_client
        self._validators = validators
        self._dao = dao

    async def generate(
        self,
        concept: ConceptNode,
        lesson_graph: LessonGraph,
    ) -> list[AssessmentItem]:
        """Generate MCQs for concept; return items passing every validator."""
        messages = build_mcq_messages(concept)
        raw = await self._model.complete(messages)

        candidates = self._parse_candidates(raw, concept_id=concept.id)
        if not candidates:
            return []

        primary_span = concept.source_spans[0]
        accepted: list[AssessmentItem] = []

        for index, cand in enumerate(candidates):
            if not cand.correct_answer.strip() or not cand.rationale.strip():
                _logger.warning(
                    "mcq_discarded",
                    reason="empty correct_answer or rationale",
                    concept_id=concept.id,
                    index=index,
                )
                continue

            if cand.correct_answer not in cand.options:
                _logger.warning(
                    "mcq_discarded",
                    reason="correct_answer not in options",
                    concept_id=concept.id,
                    index=index,
                )
                continue

            if len(cand.options) != 4:
                _logger.warning(
                    "mcq_discarded",
                    reason="options length is not 4",
                    concept_id=concept.id,
                    index=index,
                )
                continue

            item = AssessmentItem(
                id=uuid.uuid4().hex,
                kind="mcq",
                prompt=cand.prompt,
                rationale=cand.rationale,
                source_spans=[primary_span],
                difficulty=cand.difficulty,
                concept_id=concept.id,
                correct_answer=cand.correct_answer,
                bloom_level=cand.bloom_level,
            )

            payload = ItemValidationPayload(item=item, lesson_graph=lesson_graph)
            failed = False
            for validator in self._validators:
                result = validator.validate(payload)
                if not result.passed:
                    _logger.warning(
                        "mcq_discarded",
                        reason=result.reason or "validator failed",
                        concept_id=concept.id,
                        index=index,
                    )
                    failed = True
                    break
            if failed:
                continue

            await self._dao.add_assessment_item(item)
            accepted.append(item)

        return accepted

    def _parse_candidates(self, raw: str, *, concept_id: str) -> list[_ModelMCQ]:
        """Parse the model's JSON-array response. Returns [] on any failure."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            _logger.warning(
                "mcq_parse_failed",
                reason=f"invalid JSON: {exc}",
                concept_id=concept_id,
            )
            return []

        if not isinstance(data, list):
            _logger.warning(
                "mcq_parse_failed",
                reason="model response was not a JSON array",
                concept_id=concept_id,
            )
            return []

        candidates: list[_ModelMCQ] = []
        for index, raw_item in enumerate(data):
            try:
                candidates.append(_ModelMCQ.model_validate(raw_item))
            except ValidationError as exc:
                _logger.warning(
                    "mcq_parse_failed",
                    reason=f"item schema invalid: {exc}",
                    concept_id=concept_id,
                    index=index,
                )
                continue
        return candidates
