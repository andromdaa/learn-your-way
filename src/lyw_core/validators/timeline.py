"""Timeline validator: structural checks on Mermaid timeline source.

`TimelineValidator` implements `Validator[str]`. It performs cheap textual
checks that catch the common generator failure modes: empty output,
missing preamble, no section markers, and empty section titles.
"""

from __future__ import annotations

from .base import ValidationResult


class TimelineValidator:
    """Validate that a Mermaid string has the minimum timeline shape."""

    def validate(self, payload: str) -> ValidationResult:
        stripped = payload.lstrip()
        if not stripped:
            return ValidationResult(
                passed=False,
                reason="timeline payload is empty",
            )

        first_token = stripped.split(None, 1)[0]
        if first_token != "timeline":
            return ValidationResult(
                passed=False,
                reason=(
                    f"timeline preamble must start with 'timeline', got '{first_token}'"
                ),
            )

        # Find all section lines and check they have a non-empty title.
        section_count = 0
        for line in payload.splitlines():
            stripped_line = line.strip()
            if stripped_line.startswith("section"):
                section_title = stripped_line[len("section") :].strip()
                if not section_title:
                    return ValidationResult(
                        passed=False,
                        reason="timeline contains a section with an empty title",
                    )
                section_count += 1

        if section_count == 0:
            return ValidationResult(
                passed=False,
                reason="timeline must have at least one section",
            )

        return ValidationResult(passed=True)
