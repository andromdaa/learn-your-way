"""Profiles endpoints — create, list, retrieve, update, and delete learner profiles."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
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


@router.get(
    "/profiles",
    response_model=list[LearnerProfile],
    operation_id="listProfiles",
)
async def list_profiles(
    db: Annotated[Database, Depends(get_db)],
) -> list[LearnerProfile]:
    return await db.list_profiles()


@router.get(
    "/profiles/{profile_id}",
    response_model=LearnerProfile,
    operation_id="getProfile",
)
async def get_profile(
    profile_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> LearnerProfile:
    profile = await db.get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


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


@router.put(
    "/profiles/{profile_id}",
    response_model=LearnerProfile,
    operation_id="updateProfile",
)
async def update_profile(
    profile_id: str,
    body: CreateProfileRequest,
    db: Annotated[Database, Depends(get_db)],
) -> LearnerProfile:
    existing = await db.get_profile(profile_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    updated = LearnerProfile(
        id=profile_id,
        grade_level=body.grade_level,
        interests=body.interests,
        goals=body.goals,
    )
    await db.add_profile(updated)
    return updated


@router.delete(
    "/profiles/{profile_id}",
    status_code=204,
    operation_id="deleteProfile",
)
async def delete_profile(
    profile_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> None:
    deleted = await db.delete_profile(profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Profile not found")
