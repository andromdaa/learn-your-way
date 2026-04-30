"""Application-level learner profile model.

Lives in lyw_core (not lesson_graph) because it represents user state,
not canonical lesson content. No SCHEMA_CHANGE=1 required.
"""

from pydantic import BaseModel, field_validator


class LearnerProfile(BaseModel):
    """A learner's personalisation profile.

    Consumed by POST /profiles (T2) and personalization generators (T5, T7).
    """

    id: str
    grade_level: str
    interests: list[str]
    goals: list[str]

    @field_validator("grade_level")
    @classmethod
    def _grade_level_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("grade_level must not be empty")
        return v
