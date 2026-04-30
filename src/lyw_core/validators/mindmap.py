"""Mind-map validator: structural checks on Mermaid source.

`MindMapValidator` implements `Validator[str]`. It performs cheap textual
checks that catch the common generator failure modes: empty output,
missing preamble, single-node diagrams, and empty node labels.
"""

from __future__ import annotations

from .base import ValidationResult


class MindMapValidator:
    """Validate that a Mermaid string has the minimum mind-map shape."""

    def validate(self, payload: str) -> ValidationResult:
        stripped = payload.lstrip()
        if not stripped:
            return ValidationResult(
                passed=False,
                reason="mind-map payload is empty",
            )

        first_token = stripped.split(None, 1)[0]
        if first_token not in {"flowchart", "graph"}:
            return ValidationResult(
                passed=False,
                reason=(
                    f"mind-map preamble must start with 'flowchart' or 'graph', "
                    f"got '{first_token}'"
                ),
            )

        if '[""]' in payload:
            return ValidationResult(
                passed=False,
                reason="mind-map contains an empty node label",
            )

        node_count = payload.count('["')
        if node_count < 2:
            return ValidationResult(
                passed=False,
                reason=f"mind-map must have at least 2 nodes, found {node_count}",
            )

        return ValidationResult(passed=True)
