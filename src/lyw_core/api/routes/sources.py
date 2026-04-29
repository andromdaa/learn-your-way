"""POST /sources — upload and parse a source document."""

from __future__ import annotations

import hashlib
from typing import Annotated, Literal

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from lyw_core.api.app import get_arq_redis, get_data_dir, get_db
from lyw_core.db.dao import Database
from lyw_core.storage.fs import DataDir

router = APIRouter()


class SourceResponse(BaseModel):
    id: str
    title: str
    status: Literal["parsing", "ready", "failed"]


@router.post(
    "/sources",
    status_code=202,
    response_model=SourceResponse,
    operation_id="createSource",
)
async def create_source(
    file: UploadFile,
    db: Annotated[Database, Depends(get_db)],
    data_dir: Annotated[DataDir, Depends(get_data_dir)],
    arq_redis: Annotated[ArqRedis, Depends(get_arq_redis)],
    title: Annotated[str | None, Form()] = None,
) -> JSONResponse:
    data = await file.read()
    sha256 = hashlib.sha256(data).hexdigest()
    doc_id = sha256
    filename = file.filename or f"{sha256[:8]}.pdf"
    dest = data_dir.write_source(filename, data)
    if await db.get_source(doc_id) is None:
        await db.add_source(doc_id=doc_id, path=str(dest), sha256=sha256)
    await arq_redis.enqueue_job("ingest_source", source_path=str(dest), doc_id=doc_id)
    body = SourceResponse(id=doc_id, title=title or filename, status="parsing")
    return JSONResponse(content=body.model_dump(), status_code=202)
