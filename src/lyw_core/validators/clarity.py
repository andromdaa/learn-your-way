"""Clarity of learning intentions validator for AssessmentItem.

Confirms item.concept_id resolves to a ConceptNode in the lesson graph
and that the node has a non-empty learning_objective.
"""

from __future__ import annotations

from .base import ValidationResult
from .faithfulness import ItemValidationPayload


class ClarityValidator:
    """Validates that an AssessmentItem names a real concept with a learning objective."""

    def validate(self, payload: ItemValidationPayload) -> ValidationResult:
        item = payload.item
        concept = next(
            (c for c in payload.lesson_graph.concepts if c.id == item.concept_id),
            None,
        )
        if concept is None:
            return ValidationResult(
                passed=False,
                reason=f"concept_id '{item.concept_id}' not found in lesson graph",
            )
        if not concept.learning_objective.strip():
            return ValidationResult(
                passed=False,
                reason=f"concept '{item.concept_id}' has empty learning_objective",
            )
        return ValidationResult(passed=True)
