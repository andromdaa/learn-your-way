"""Slide generator: produces a structured slide deck from a lesson graph.

``SlideGenerator`` uses a two-step approach:

1. **Outline step**: one model call returns a JSON array of
   ``SlideOutlineItem`` objects (title, key points, concept_id).
2. **Flesh-out step**: one model call per outline item returns body text
   and speaker notes for each slide.

Slides that fail ``SlideValidator`` are discarded with a structlog warning
(matching the ``MCQGenerator`` per-item discard pattern from ADR-0011).
If all slides are discarded, ``ValidationError`` is raised.

No persistence is done here — that belongs in the Arq job (T6).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import structlog
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from lesson_graph.interfaces import ModelClient
from lesson_graph.models import LessonGraph, PersonalizationProfile, SourceSpan
from lyw_core.modalities.prompts.slides import (
    build_slide_body_messages,
    build_slide_outline_messages,
)
from lyw_core.validators.base import ValidationError
from lyw_core.validators.slides import SlideValidator

_logger = structlog.get_logger(__name__)


@dataclass
class Slide:
    """A single slide in a deck.

    Attributes:
        title: Slide headline.
        body: Main slide body text.
        speaker_notes: Presenter notes.
        source_spans: Source spans grounding the slide content.
        concept_id: The concept this slide is derived from.
    """

    title: str
    body: str
    speaker_notes: str
    source_spans: list[SourceSpan]
    concept_id: str


@dataclass
class SlideDeck:
    """A collection of slides produced from a lesson graph.

    Attributes:
        slides: Accepted slides (failed slides discarded by the generator).
        based_on_concepts: Concept IDs represented in the deck.
    """

    slides: list[Slide]
    based_on_concepts: list[str] = field(default_factory=list)


class SlideOutlineItem(BaseModel):
    """Schema for one element of the model's JSON-array outline response."""

    title: str
    key_points: list[str]
    concept_id: str


class _SlideBody(BaseModel):
    """Schema for the model's JSON body response for a single slide."""

    body: str
    speaker_notes: str


class SlideGenerator:
    """Async slide generator using a two-step LLM approach.

    Stateless; a single instance can be reused across requests.
    """

    async def generate(
        self,
        lesson_graph: LessonGraph,
        profile: PersonalizationProfile,
        model_client: ModelClient,
    ) -> SlideDeck:
        """Generate a slide deck from ``lesson_graph``.

        Args:
            lesson_graph: Source lesson graph.
            profile: Learner personalization profile.
            model_client: Async model client for LLM calls.

        Returns:
            A ``SlideDeck`` containing all accepted slides.

        Raises:
            ValidationError: If the outline JSON is malformed or all slides
                are discarded by the validator.
        """
        # Step 1: get slide outline from the model
        outline_items = await self._get_outline(lesson_graph, profile, model_client)

        # Build concept index for source span lookup
        concept_index = {c.id: c for c in lesson_graph.concepts}

        # Step 2: flesh out each outline item; discard failures
        validator = SlideValidator()
        accepted: list[Slide] = []

        for item in outline_items:
            concept = concept_index.get(item.concept_id)
            if concept is None:
                _logger.warning(
                    "slide_outline_item_skipped",
                    reason="concept_id not found in lesson graph",
                    concept_id=item.concept_id,
                    title=item.title,
                )
                continue

            slide = await self._flesh_out_slide(
                item=item,
                source_spans=concept.source_spans,
                model_client=model_client,
            )
            if slide is None:
                continue

            result = validator.validate(slide)
            if not result.passed:
                _logger.warning(
                    "slide_discarded",
                    reason=result.reason or "validator failed",
                    title=item.title,
                    concept_id=item.concept_id,
                )
                continue

            accepted.append(slide)

        if not accepted:
            raise ValidationError(
                ["all slides were discarded; cannot produce empty deck"]
            )

        based_on = list({s.concept_id for s in accepted})
        return SlideDeck(slides=accepted, based_on_concepts=based_on)

    async def _get_outline(
        self,
        lesson_graph: LessonGraph,
        profile: PersonalizationProfile,
        model_client: ModelClient,
    ) -> list[SlideOutlineItem]:
        """Call the model for the outline; parse and validate the JSON response."""
        messages = build_slide_outline_messages(lesson_graph, profile)
        raw = await model_client.complete(messages)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValidationError([f"outline JSON parse failed: {exc}"]) from exc

        if not isinstance(data, list):
            raise ValidationError(["outline response was not a JSON array"])

        items: list[SlideOutlineItem] = []
        for index, raw_item in enumerate(data):
            try:
                items.append(SlideOutlineItem.model_validate(raw_item))
            except PydanticValidationError as exc:
                _logger.warning(
                    "slide_outline_item_invalid",
                    reason=str(exc),
                    index=index,
                )
                continue

        return items

    async def _flesh_out_slide(
        self,
        *,
        item: SlideOutlineItem,
        source_spans: list[SourceSpan],
        model_client: ModelClient,
    ) -> Slide | None:
        """Call the model for body + speaker notes for one slide.

        Returns ``None`` if the model response cannot be parsed.
        """
        messages = build_slide_body_messages(item.title, item.key_points)
        raw = await model_client.complete(messages)

        try:
            body_data = _SlideBody.model_validate_json(raw)
        except PydanticValidationError as exc:
            _logger.warning(
                "slide_body_parse_failed",
                reason=str(exc),
                title=item.title,
                concept_id=item.concept_id,
            )
            return None

        return Slide(
            title=item.title,
            body=body_data.body,
            speaker_notes=body_data.speaker_notes,
            source_spans=list(source_spans),
            concept_id=item.concept_id,
        )
