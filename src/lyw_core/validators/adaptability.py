"""Adaptability validator: releveled text must be strictly closer to target grade."""

from __future__ import annotations

from dataclasses import dataclass

import textstat

from lyw_core.validators.base import ValidationResult


@dataclass(frozen=True)
class AdaptabilityPayload:
    original: str
    releveled: str
    target_grade: int


class AdaptabilityValidator:
    def validate(self, payload: AdaptabilityPayload) -> ValidationResult:
        orig_fk = textstat.flesch_kincaid_grade(payload.original)
        rel_fk = textstat.flesch_kincaid_grade(payload.releveled)
        target = payload.target_grade

        orig_dist = abs(orig_fk - target)
        rel_dist = abs(rel_fk - target)

        if orig_dist == 0.0 or rel_dist < orig_dist:
            return ValidationResult(passed=True)

        return ValidationResult(
            passed=False,
            reason=(
                f"releveled grade {rel_fk} is not closer to target {target} "
                f"than original grade {orig_fk} "
                f"(orig_dist={orig_dist:.1f}, rel_dist={rel_dist:.1f})"
            ),
        )
