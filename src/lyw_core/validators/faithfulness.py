"""Source faithfulness validator for personalization generators.

Confirms every cited span falls within the character-offset range of at
least one SourceSpan on the parent concept in the lesson graph. Used by
the relevel and replace generators as a faithfulness gate before
returning generated content.
"""

from __future__ import annotations

from dataclasses import dataclass

from lesson_graph.models import LessonGraph, SourceSpan

from .base import ValidationResult


@dataclass
class ItemValidationPayload:
    """Payload passed to the faithfulness validator.

    ``concept_id`` selects the parent concept whose ``source_spans`` the
    candidate ``spans`` must be contained in.
    """

    concept_id: str
    spans: list[SourceSpan]
    lesson_graph: LessonGraph


def span_is_contained(item_span: SourceSpan, concept_spans: list[SourceSpan]) -> bool:
    """Return True if item_span falls within any concept span.

    A span is "within" a concept span when doc_id matches, pages overlap,
    and the character range is fully contained.
    """
    for cs in concept_spans:
        pages_overlap = (
            item_span.page_start <= cs.page_end and item_span.page_end >= cs.page_start
        )
        chars_contained = (
            item_span.char_start >= cs.char_start and item_span.char_end <= cs.char_end
        )
        if item_span.doc_id == cs.doc_id and pages_overlap and chars_contained:
            return True
    return False


class SourceFaithfulnessValidator:
    """Validates that every candidate span is within its parent concept's spans."""

    def validate(self, payload: ItemValidationPayload) -> ValidationResult:
        concept = next(
            (c for c in payload.lesson_graph.concepts if c.id == payload.concept_id),
            None,
        )
        if concept is None:
            return ValidationResult(
                passed=False,
                reason=f"concept_id {payload.concept_id!r} not found in lesson graph",
            )

        failing = [
            span
            for span in payload.spans
            if not span_is_contained(span, concept.source_spans)
        ]
        if failing:
            return ValidationResult(
                passed=False,
                reason="payload cites spans outside concept's source range",
                evidence=failing,
            )
        return ValidationResult(passed=True)
