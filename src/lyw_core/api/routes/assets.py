"""GET /v1/assets/{asset_id} — retrieve a derived asset by ID."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, Response

from lyw_core.api.app import get_db
from lyw_core.db.dao import Database

router = APIRouter()

_CONTENT_TYPES: dict[str, str] = {
    ".json": "application/json",
    ".mmd": "text/plain",
    ".txt": "text/plain",
}


@router.get(
    "/v1/assets/{asset_id}",
    operation_id="getDerivedAsset",
)
async def get_derived_asset(
    asset_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> Response:
    """Return the file content of a derived asset by its ID.

    Returns the file content with content-type ``application/json`` for
    ``.json`` files and ``text/plain`` for ``.mmd`` / ``.txt`` files.
    Returns 404 if the asset is not found in the database or if the
    backing file has been removed from storage.
    """
    asset = await db.get_derived_asset_by_id(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    file_path = Path(asset.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Asset file not found on disk",
        )

    suffix = file_path.suffix.lower()
    content_type = _CONTENT_TYPES.get(suffix, "application/octet-stream")

    content = file_path.read_bytes()

    if content_type == "application/json":
        return Response(content=content, media_type="application/json")
    return PlainTextResponse(content=content.decode("utf-8"), media_type=content_type)
