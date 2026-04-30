"""Unit tests for TimelineValidator."""

from __future__ import annotations

from lyw_core.validators.timeline import TimelineValidator


def _valid_timeline() -> str:
    return "timeline\n    section Event One\n        First event text\n    section Event Two\n        Second event text\n"


def test_valid_timeline_passes() -> None:
    result = TimelineValidator().validate(_valid_timeline())
    assert result.passed is True
    assert result.reason is None


def test_empty_string_fails() -> None:
    result = TimelineValidator().validate("")
    assert result.passed is False
    assert result.reason is not None
    assert "empty" in result.reason


def test_whitespace_only_fails() -> None:
    result = TimelineValidator().validate("   \n\n  ")
    assert result.passed is False


def test_missing_preamble_fails() -> None:
    payload = "    section Event One\n        Something happened\n"
    result = TimelineValidator().validate(payload)
    assert result.passed is False
    assert result.reason is not None
    assert "preamble" in result.reason


def test_wrong_preamble_keyword_fails() -> None:
    payload = "flowchart TD\n    section Event One\n        Something\n"
    result = TimelineValidator().validate(payload)
    assert result.passed is False


def test_no_sections_fails() -> None:
    payload = "timeline\n    This has no section markers\n"
    result = TimelineValidator().validate(payload)
    assert result.passed is False
    assert result.reason is not None
    assert "section" in result.reason


def test_single_section_passes() -> None:
    """A single section is valid — there is no minimum section count."""
    payload = "timeline\n    section Only Event\n        Something happened here\n"
    result = TimelineValidator().validate(payload)
    assert result.passed is True


def test_empty_section_title_fails() -> None:
    """A section with no title after 'section' is invalid."""
    payload = "timeline\n    section\n        Something\n"
    result = TimelineValidator().validate(payload)
    assert result.passed is False
    assert result.reason is not None
    assert "empty" in result.reason.lower() or "section" in result.reason.lower()


def test_multiple_sections_all_valid_passes() -> None:
    payload = (
        "timeline\n"
        "    section Ancient Times\n"
        "        Pyramids built\n"
        "    section Medieval Era\n"
        "        Castles constructed\n"
        "    section Modern Era\n"
        "        Internet invented\n"
    )
    result = TimelineValidator().validate(payload)
    assert result.passed is True
