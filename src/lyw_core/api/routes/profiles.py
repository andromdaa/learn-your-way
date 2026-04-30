"""POST /profiles — create or update a learner profile."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator

from lyw_core.api.app import get_db
from lyw_core.db.dao import Database
from lyw_core.profiles.models import LearnerProfile

router = APIRouter()


class CreateProfileRequest(BaseModel):
    grade_level: str
    interests: list[str] = []
    goals: list[str] = []

    @field_validator("grade_level")
    @classmethod
    def _grade_level_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("grade_level must not be empty")
        return v


@router.post(
    "/profiles",
    response_model=LearnerProfile,
    operation_id="createProfile",
)
async def create_profile(
    body: CreateProfileRequest,
    db: Annotated[Database, Depends(get_db)],
) -> LearnerProfile:
    profile = LearnerProfile(
        id=str(uuid.uuid4()),
        grade_level=body.grade_level,
        interests=body.interests,
        goals=body.goals,
    )
    await db.add_profile(profile)
    return profile
