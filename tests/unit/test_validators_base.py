"""Unit tests for the validator framework (ValidationResult, Validator, run_validators)."""

import pytest

from lyw_core.validators.base import (  # noqa: F401 — Validator exercised via Protocol structural check
    ValidationError,
    ValidationResult,
    Validator,
    run_validators,
)

# ---------------------------------------------------------------------------
# Minimal concrete validators for test use
# ---------------------------------------------------------------------------


class AlwaysPass:
    def validate(self, payload: str) -> ValidationResult:
        return ValidationResult(passed=True)


class AlwaysFail:
    def __init__(self, reason: str = "failed") -> None:
        self._reason = reason

    def validate(self, payload: str) -> ValidationResult:
        return ValidationResult(passed=False, reason=self._reason)


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------


def test_validation_result_passed_defaults() -> None:
    r = ValidationResult(passed=True)
    assert r.passed is True
    assert r.reason is None
    assert r.evidence is None


def test_validation_result_failed_with_reason() -> None:
    r = ValidationResult(passed=False, reason="no source span")
    assert r.passed is False
    assert r.reason == "no source span"


def test_validation_result_is_frozen() -> None:
    r = ValidationResult(passed=True)
    with pytest.raises((AttributeError, TypeError)):
        r.passed = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# run_validators
# ---------------------------------------------------------------------------


def test_run_validators_all_pass() -> None:
    run_validators([AlwaysPass(), AlwaysPass()], "payload")


def test_run_validators_single_fail_raises() -> None:
    with pytest.raises(ValidationError) as exc_info:
        run_validators([AlwaysPass(), AlwaysFail("bad span")], "payload")
    assert "bad span" in exc_info.value.reasons


def test_run_validators_multi_fail_collects_all_reasons() -> None:
    with pytest.raises(ValidationError) as exc_info:
        run_validators(
            [AlwaysFail("reason one"), AlwaysFail("reason two")],
            "payload",
        )
    assert "reason one" in exc_info.value.reasons
    assert "reason two" in exc_info.value.reasons
    assert len(exc_info.value.reasons) == 2


def test_run_validators_error_message_lists_reasons() -> None:
    with pytest.raises(ValidationError) as exc_info:
        run_validators([AlwaysFail("x"), AlwaysFail("y")], "payload")
    msg = str(exc_info.value)
    assert "x" in msg
    assert "y" in msg


def test_run_validators_fallback_reason_when_none() -> None:
    """validator returning passed=False with reason=None gets a fallback message."""

    class NoReason:
        def validate(self, payload: str) -> ValidationResult:
            return ValidationResult(passed=False)

    with pytest.raises(ValidationError) as exc_info:
        run_validators([NoReason()], "payload")
    assert len(exc_info.value.reasons) == 1
    assert exc_info.value.reasons[0]  # non-empty fallback


def test_validation_error_carries_reasons() -> None:
    err = ValidationError(["a", "b"])
    assert err.reasons == ["a", "b"]


def test_run_validators_empty_list_passes() -> None:
    run_validators([], "payload")
