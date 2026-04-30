"""Slide validator: structural checks on a single Slide.

``SlideValidator`` implements ``Validator[Slide]``. It checks the four
source-fidelity invariants required by the spec:
- non-empty title
- non-empty body
- non-empty source_spans
- non-empty concept_id

The validator accepts any object with the Slide duck-type interface to
avoid a circular import between lyw_core.modalities.slides and this module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import ValidationResult

if TYPE_CHECKING:
    pass


class SlideValidator:
    """Validate that a single Slide meets the minimum structural requirements."""

    def validate(self, payload: Any) -> ValidationResult:  # Slide at runtime
        if not payload.title.strip():
            return ValidationResult(
                passed=False,
                reason="slide title is empty",
            )

        if not payload.body.strip():
            return ValidationResult(
                passed=False,
                reason="slide body is empty",
            )

        if not payload.source_spans:
            return ValidationResult(
                passed=False,
                reason="slide has no source spans (source fidelity required)",
            )

        if not payload.concept_id.strip():
            return ValidationResult(
                passed=False,
                reason="slide concept_id is empty",
            )

        return ValidationResult(passed=True)
