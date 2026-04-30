"""Validator framework: ValidationResult, Validator protocol, run_validators.

All validators are synchronous. Async generators call them inline before
returning their output. See ADR-0011 for design rationale.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar, runtime_checkable

from lesson_graph.models import SourceSpan


@dataclass(frozen=True)
class ValidationResult:
    """Immutable result of a single validator run."""

    passed: bool
    reason: str | None = None
    evidence: list[SourceSpan] | None = None


class ValidationError(Exception):
    """Raised by run_validators when one or more validators return passed=False."""

    def __init__(self, reasons: list[str]) -> None:
        self.reasons = reasons
        super().__init__("; ".join(reasons))


_T_contra = TypeVar("_T_contra", contravariant=True)


@runtime_checkable
class Validator(Protocol[_T_contra]):
    """Single-method protocol every validator must satisfy."""

    def validate(self, payload: _T_contra) -> ValidationResult: ...


def run_validators[T](
    validators: Sequence[Validator[T]],
    payload: T,
) -> None:
    """Run all validators against payload.

    Collects every failure before raising so callers see all problems at once.
    Raises ValidationError if any validator returns passed=False.
    """
    failed: list[str] = []
    for v in validators:
        result = v.validate(payload)
        if not result.passed:
            failed.append(result.reason or "validation failed")
    if failed:
        raise ValidationError(failed)
