"""Shared Pydantic response models used across multiple route modules."""

from __future__ import annotations

from pydantic import BaseModel


class StoredDerivedAsset(BaseModel):
    """API shape of a persisted derived asset.

    Mirrors ``lyw_core.db.dao.DerivedAsset`` (the DAO dataclass). Distinct from
    ``lesson_graph.models.DerivedAsset`` (the generator-output Pydantic domain model).
    """

    id: str
    lesson_id: str
    concept_id: str
    kind: str
    profile_id: str
    file_path: str
    created_at: str
