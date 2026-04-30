"""Unit tests for LearnerProfile model and profile DAO methods.

All tests use an in-memory SQLite database — no filesystem, no services.
"""

import pytest
from pydantic import ValidationError

from lyw_core.db import Database
from lyw_core.profiles.models import LearnerProfile


def _profile(
    id: str = "p1",
    grade_level: str = "8",
    interests: list[str] | None = None,
    goals: list[str] | None = None,
) -> LearnerProfile:
    return LearnerProfile(
        id=id,
        grade_level=grade_level,
        interests=interests if interests is not None else ["football"],
        goals=goals if goals is not None else ["pass exam"],
    )


# ---------------------------------------------------------------------------
# LearnerProfile model
# ---------------------------------------------------------------------------


def test_learner_profile_valid() -> None:
    p = _profile()
    assert p.id == "p1"
    assert p.grade_level == "8"


def test_learner_profile_rejects_empty_grade_level() -> None:
    with pytest.raises(ValidationError):
        _profile(grade_level="")


def test_learner_profile_rejects_whitespace_grade_level() -> None:
    with pytest.raises(ValidationError):
        _profile(grade_level="   ")


def test_learner_profile_interests_and_goals_round_trip() -> None:
    p = LearnerProfile.model_validate_json(
        _profile(
            interests=["coding", "chess"], goals=["improve", "compete"]
        ).model_dump_json()
    )
    assert p.interests == ["coding", "chess"]
    assert p.goals == ["improve", "compete"]


def test_learner_profile_empty_interests_and_goals_allowed() -> None:
    p = _profile(interests=[], goals=[])
    assert p.interests == []
    assert p.goals == []


# ---------------------------------------------------------------------------
# Profile DAO
# ---------------------------------------------------------------------------


async def test_add_and_get_profile_round_trip() -> None:
    db = await Database.connect(":memory:")
    profile = _profile()
    await db.add_profile(profile)
    retrieved = await db.get_profile("p1")
    assert retrieved is not None
    assert retrieved.id == profile.id
    assert retrieved.grade_level == profile.grade_level
    assert retrieved.interests == profile.interests
    assert retrieved.goals == profile.goals
    await db.close()


async def test_get_profile_missing_returns_none() -> None:
    db = await Database.connect(":memory:")
    result = await db.get_profile("no-such-id")
    assert result is None
    await db.close()


async def test_add_profile_upserts_on_id() -> None:
    db = await Database.connect(":memory:")
    await db.add_profile(_profile(interests=["chess"]))
    await db.add_profile(_profile(interests=["football", "coding"]))
    retrieved = await db.get_profile("p1")
    assert retrieved is not None
    assert retrieved.interests == ["football", "coding"]
    await db.close()


async def test_list_profiles_returns_all() -> None:
    db = await Database.connect(":memory:")
    await db.add_profile(_profile(id="p1", grade_level="7"))
    await db.add_profile(_profile(id="p2", grade_level="9"))
    profiles = await db.list_profiles()
    ids = {p.id for p in profiles}
    assert ids == {"p1", "p2"}
    await db.close()


async def test_list_profiles_empty() -> None:
    db = await Database.connect(":memory:")
    profiles = await db.list_profiles()
    assert profiles == []
    await db.close()
