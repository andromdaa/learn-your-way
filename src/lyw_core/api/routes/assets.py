"""Assets endpoints — retrieve derived assets by ID or composite key."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, Response

from lyw_core.api.app import get_db
from lyw_core.api.schemas import StoredDerivedAsset
from lyw_core.db.dao import Database

router = APIRouter()


_CONTENT_TYPES: dict[str, str] = {
    ".json": "application/json",
    ".mmd": "text/plain",
    ".txt": "text/plain",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".html": "text/html",
}

_BINARY_TYPES = {"image/png"}


def _asset_response(file_path: Path) -> Response:
    suffix = file_path.suffix.lower()
    content_type = _CONTENT_TYPES.get(suffix, "application/octet-stream")
    content = file_path.read_bytes()
    if content_type in _BINARY_TYPES or content_type == "application/octet-stream":
        return Response(content=content, media_type=content_type)
    if content_type == "application/json":
        return Response(content=content, media_type="application/json")
    return PlainTextResponse(content=content.decode("utf-8"), media_type=content_type)


# /by-key must be registered before /{asset_id} to avoid the path parameter
# swallowing the literal "by-key" string.
@router.get(
    "/v1/assets/by-key",
    response_model=StoredDerivedAsset,
    operation_id="getAssetByKey",
)
async def get_asset_by_key(
    db: Annotated[Database, Depends(get_db)],
    lesson_id: Annotated[str, Query()],
    concept_id: Annotated[str, Query()],
    kind: Annotated[str, Query()],
    profile_id: Annotated[str, Query()],
) -> StoredDerivedAsset:
    asset = await db.get_derived_asset(lesson_id, concept_id, kind, profile_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return StoredDerivedAsset(
        id=asset.id,
        lesson_id=asset.lesson_id,
        concept_id=asset.concept_id,
        kind=asset.kind,
        profile_id=asset.profile_id,
        file_path=asset.file_path,
        created_at=asset.created_at,
    )


@router.get(
    "/v1/assets/{asset_id}",
    operation_id="getDerivedAsset",
)
async def get_derived_asset(
    asset_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> Response:
    asset = await db.get_derived_asset_by_id(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    file_path = Path(asset.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Asset file not found on disk")
    return _asset_response(file_path)
