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

# Minimum body-text size required before we will hand a concept to the LLM for
# example replacement. The replace prompt embeds only ``concept.summary``; if
# that is effectively just a heading or otherwise lacks teachable content, the
# LLM emits an interest-themed flourish unmoored from the source (issue #77).
# Both gates apply: 200 chars roughly equals ~30 words at average English word
# length; either signal trips the guard. A heading-only summary
# (e.g. "EQUATIONS AND INEQUALITIES") trips reliably while substantive
# single-paragraph concepts pass.
_MIN_BODY_CHARS = 200
_MIN_BODY_WORDS = 30


class ReplaceSourceTooThinError(Exception):
    """Raised when a concept's summary lacks enough teachable content to replace.

    The replace generator embeds ``concept.summary`` directly into the LLM
    prompt; when the summary is effectively a heading or otherwise too thin,
    any "replacement" the model produces is unmoored from the source. The
    orchestrator surfaces this as a ``failed`` job status (no asset persisted).
    """

    def __init__(self, concept_id: str, char_count: int, word_count: int) -> None:
        self.concept_id = concept_id
        self.char_count = char_count
        self.word_count = word_count
        super().__init__(
            f"concept {concept_id!r} summary too thin for replace generator: "
            f"{char_count} chars, {word_count} words "
            f"(min {_MIN_BODY_CHARS} chars, {_MIN_BODY_WORDS} words)"
        )


def _extract_body_text(concept: ConceptNode) -> str:
    """Return concept.summary with a leading title line stripped if present.

    The heuristic chunker falls back to ``summary = title`` when the source
    span has no body content, and substantive summaries sometimes echo the
    title in the first line. Stripping a leading title-match (case-insensitive)
    yields the actual teachable body for thresholding purposes.
    """
    summary = concept.summary.strip()
    title = concept.title.strip()
    if title and summary.lower().startswith(title.lower()):
        summary = summary[len(title) :].lstrip(" \t\n:.-")
    return summary


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

        Raises
        ------
        ReplaceSourceTooThinError
            If ``concept.summary`` (sans leading title) has fewer than
            ``_MIN_BODY_CHARS`` characters or ``_MIN_BODY_WORDS`` words. This
            pre-flight gate prevents the LLM from being asked to "replace"
            content that isn't there (issue #77). Distinct from the
            JSON-fence parse fix in #64: parsing succeeds in the thin-source
            case but the result is non-substantive because the *input* was.
        """
        body = _extract_body_text(concept)
        char_count = len(body)
        word_count = len(body.split())
        if char_count < _MIN_BODY_CHARS or word_count < _MIN_BODY_WORDS:
            _logger.warning(
                "example_replacement_source_too_thin",
                concept_id=concept.id,
                char_count=char_count,
                word_count=word_count,
                min_chars=_MIN_BODY_CHARS,
                min_words=_MIN_BODY_WORDS,
            )
            raise ReplaceSourceTooThinError(
                concept_id=concept.id,
                char_count=char_count,
                word_count=word_count,
            )

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

            result = self._faithfulness.validate(
                ItemValidationPayload(
                    concept_id=concept.id,
                    spans=[original_span],
                    lesson_graph=lesson_graph,
                )
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
