"""Section-quality validators for quiz coverage, emphasis, and active learning.

All three implement Validator[SectionQuizPayload] and are synchronous.
See docs/plans/phase-2/T10-section-quality-validators.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from lesson_graph.models import AssessmentItem, ConceptNode

from .base import ValidationResult

_ACTIVE_BLOOM = frozenset({"apply", "analyze", "evaluate", "create"})


@dataclass
class SectionQuizPayload:
    """Payload for section-level validators."""

    concepts: list[ConceptNode]
    items: list[AssessmentItem]


class CoverageValidator:
    """Fails if any concept in the section has no AssessmentItem referencing it."""

    def validate(self, payload: SectionQuizPayload) -> ValidationResult:
        covered = {item.concept_id for item in payload.items}
        uncovered = [c.id for c in payload.concepts if c.id not in covered]
        if uncovered:
            return ValidationResult(
                passed=False,
                reason=f"concepts with no items: {', '.join(uncovered)}",
            )
        return ValidationResult(passed=True)


class EmphasisValidator:
    """Fails when a high-prerequisite concept is unemphasized while low-prerequisite ones are.

    Specifically: fails if any concept with len(prerequisites) >= 2 has 0 items
    while any concept with len(prerequisites) == 0 has >= 2 items.
    """

    def validate(self, payload: SectionQuizPayload) -> ValidationResult:
        counts: dict[str, int] = {c.id: 0 for c in payload.concepts}
        for item in payload.items:
            if item.concept_id in counts:
                counts[item.concept_id] += 1

        high_prereq_empty = [
            c.id
            for c in payload.concepts
            if len(c.prerequisites) >= 2 and counts[c.id] == 0
        ]
        zero_prereq_covered = any(
            counts[c.id] >= 2 for c in payload.concepts if len(c.prerequisites) == 0
        )

        if high_prereq_empty and zero_prereq_covered:
            return ValidationResult(
                passed=False,
                reason=(
                    f"high-prerequisite concepts with 0 items while "
                    f"zero-prerequisite concepts have ≥2: {', '.join(high_prereq_empty)}"
                ),
            )
        return ValidationResult(passed=True)


class ActiveLearningValidator:
    """Fails if no item in the section targets an active Bloom's level.

    Items with bloom_level=None are treated as 'remember' (most conservative)
    so that untagged quizzes never silently pass this check.
    """

    def validate(self, payload: SectionQuizPayload) -> ValidationResult:
        has_active = any(
            (item.bloom_level or "remember") in _ACTIVE_BLOOM for item in payload.items
        )
        if not has_active:
            return ValidationResult(
                passed=False,
                reason=(
                    "no item targets an active Bloom's level "
                    "(apply/analyze/evaluate/create); "
                    "bloom_level=None is treated as 'remember'"
                ),
            )
        return ValidationResult(passed=True)
