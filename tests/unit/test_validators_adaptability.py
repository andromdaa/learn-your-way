"""Unit tests for AdaptabilityValidator — textstat is mocked for determinism."""

from unittest.mock import patch

from lyw_core.validators.adaptability import AdaptabilityPayload, AdaptabilityValidator
from lyw_core.validators.base import ValidationResult


def _payload(
    original: str = "original text",
    releveled: str = "releveled text",
    target_grade: int = 5,
) -> AdaptabilityPayload:
    return AdaptabilityPayload(
        original=original, releveled=releveled, target_grade=target_grade
    )


def _validate(orig_fk: float, rel_fk: float, target: int = 5) -> ValidationResult:
    with patch(
        "lyw_core.validators.adaptability.textstat.flesch_kincaid_grade"
    ) as mock_fk:
        mock_fk.side_effect = [orig_fk, rel_fk]
        return AdaptabilityValidator().validate(_payload(target_grade=target))


# ---------------------------------------------------------------------------
# Pass cases
# ---------------------------------------------------------------------------


def test_adaptability_passes_when_releveled_closer_to_target() -> None:
    # original=10, target=5, releveled=6: dist 5→1, pass
    result = _validate(orig_fk=10.0, rel_fk=6.0, target=5)
    assert result.passed is True


def test_adaptability_passes_when_releveling_overshoots_but_closer() -> None:
    # original=8, target=5, releveled=3: dist 3→2, pass (3 is closer to 5)
    result = _validate(orig_fk=8.0, rel_fk=3.0, target=5)
    assert result.passed is True


def test_adaptability_passes_when_original_already_at_target() -> None:
    # original already at target — nothing to improve, pass
    result = _validate(orig_fk=5.0, rel_fk=7.0, target=5)
    assert result.passed is True


def test_adaptability_passes_when_releveled_exactly_at_target() -> None:
    result = _validate(orig_fk=10.0, rel_fk=5.0, target=5)
    assert result.passed is True


# ---------------------------------------------------------------------------
# Fail cases
# ---------------------------------------------------------------------------


def test_adaptability_fails_when_releveled_further_from_target() -> None:
    # original=6, target=5, releveled=8: dist 1→3, fail
    result = _validate(orig_fk=6.0, rel_fk=8.0, target=5)
    assert result.passed is False


def test_adaptability_fail_reason_includes_grades() -> None:
    result = _validate(orig_fk=6.0, rel_fk=8.0, target=5)
    reason = result.reason or ""
    assert "6.0" in reason
    assert "8.0" in reason
    assert "5" in reason


def test_adaptability_fails_when_same_distance() -> None:
    # original=6, target=5, releveled=4: dist 1→1, not strictly closer, fail
    result = _validate(orig_fk=6.0, rel_fk=4.0, target=5)
    assert result.passed is False
