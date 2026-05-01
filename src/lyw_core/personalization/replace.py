"""Example-replacement generator: swaps personalizable segments for interest-linked ones.

Returns a list of ReplacementRecord. Each candidate is gated by the source
faithfulness validator; failures are discarded with a warning log rather than
raised, so a single bad replacement does not abort a personalization run.
See docs/plans/phase-2/T7-example-replacement.md.
"""

from __future__ import annotations

import json
import re

import structlog
from pydantic import BaseModel, ValidationError

from lesson_graph.interfaces import ModelClient
from lesson_graph.models import (
    AssessmentItem,
    ConceptNode,
    LessonGraph,
    ReplacementRecord,
)
from lyw_core.personalization.prompts.replace import build_replace_messages
from lyw_core.profiles.models import LearnerProfile
from lyw_core.validators.faithfulness import (
    ItemValidationPayload,
    SourceFaithfulnessValidator,
)

_logger = structlog.get_logger(__name__)


class _ModelReplacement(BaseModel):
    """Schema for one element in the model's JSON-array response."""

    original_text: str
    replacement_text: str
    interest: str


class ExampleReplacer:
    """Replaces analogies/scenarios/examples with interest-linked alternatives.

    The faithfulness validator is consulted for each candidate; replacements
    that fail are discarded and a warning is logged. The caller appends the
    returned records to PersonalizationProfile.replacements.
    """

    def __init__(
        self,
        model_client: ModelClient,
        faithfulness_validator: SourceFaithfulnessValidator,
    ) -> None:
        self._model = model_client
        self._faithfulness = faithfulness_validator

    async def replace(
        self,
        concept: ConceptNode,
        profile: LearnerProfile,
        lesson_graph: LessonGraph,
    ) -> list[ReplacementRecord]:
        """Generate interest-linked replacements for personalizable segments.

        Returns the list of accepted ReplacementRecords. Replacements failing
        the faithfulness gate are discarded (warning logged), not raised.
        """
        messages = build_replace_messages(concept, profile)
        raw = await self._model.complete(messages)

        candidates = self._parse_candidates(raw, concept_id=concept.id)
        if not candidates:
            return []

        original_span = concept.source_spans[0]
        accepted: list[ReplacementRecord] = []

        for index, cand in enumerate(candidates):
            if not cand.replacement_text.strip():
                _logger.warning(
                    "example_replacement_discarded",
                    reason="empty replacement_text",
                    concept_id=concept.id,
                    index=index,
                )
                continue

            check_item = AssessmentItem(
                id=f"__replace_check_{index}__",
                kind="short_answer",
                prompt=cand.original_text[:200] or concept.summary[:200],
                rationale="faithfulness gate for example replacement",
                source_spans=[original_span],
                difficulty="easy",
                concept_id=concept.id,
            )
            result = self._faithfulness.validate(
                ItemValidationPayload(item=check_item, lesson_graph=lesson_graph)
            )
            if not result.passed:
                _logger.warning(
                    "example_replacement_discarded",
                    reason=result.reason or "faithfulness validation failed",
                    concept_id=concept.id,
                    index=index,
                    interest=cand.interest,
                )
                continue

            accepted.append(
                ReplacementRecord(
                    original_span=original_span,
                    replacement_text=cand.replacement_text,
                    justification=f"replaced analogy with interest: {cand.interest}",
                )
            )

        return accepted

    @staticmethod
    def _strip_fences(raw: str) -> str:
        """Strip markdown code fences from a model response.

        Handles ` ```json`, ` ```JSON`, and bare ` ``` ` wrappers so that
        models (e.g. gemma3:4b) which wrap their JSON array in fences do not
        cause a spurious JSONDecodeError.
        """
        stripped = raw.strip()
        match = re.fullmatch(
            r"```(?:json|JSON)?\s*\n?(.*?)\n?```",
            stripped,
            re.DOTALL,
        )
        if match:
            return match.group(1).strip()
        return raw

    def _parse_candidates(
        self, raw: str, *, concept_id: str
    ) -> list[_ModelReplacement]:
        """Parse the model's JSON-array response. Returns [] on any failure."""
        try:
            data = json.loads(self._strip_fences(raw))
        except json.JSONDecodeError as exc:
            _logger.warning(
                "example_replacement_parse_failed",
                reason=f"invalid JSON: {exc}",
                concept_id=concept_id,
            )
            return []

        if not isinstance(data, list):
            _logger.warning(
                "example_replacement_parse_failed",
                reason="model response was not a JSON array",
                concept_id=concept_id,
            )
            return []

        candidates: list[_ModelReplacement] = []
        for index, item in enumerate(data):
            try:
                candidates.append(_ModelReplacement.model_validate(item))
            except ValidationError as exc:
                _logger.warning(
                    "example_replacement_parse_failed",
                    reason=f"item schema invalid: {exc}",
                    concept_id=concept_id,
                    index=index,
                )
                continue
        return candidates
