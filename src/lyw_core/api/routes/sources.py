"""Sources endpoints — upload, list, retrieve, and excerpt source documents."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Annotated, Literal

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from lyw_core.api.app import get_arq_redis, get_data_dir, get_db, get_parsed_doc_cache
from lyw_core.db.dao import Database, SourceRow
from lyw_core.parser.excerpt import extract_excerpt
from lyw_core.parser.models import ParsedDocument
from lyw_core.storage.fs import DataDir

router = APIRouter()


class SourceResponse(BaseModel):
    id: str
    title: str
    status: Literal["parsing", "ready", "failed"]
    job_id: str | None = None


class SourceDetail(BaseModel):
    doc_id: str
    path: str
    sha256: str
    created_at: str
    lesson_id: str | None


class ExcerptResponse(BaseModel):
    text: str
    doc_id: str
    char_start: int
    char_end: int
    window_start: int


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
    job = await arq_redis.enqueue_job(
        "ingest_source", source_path=str(dest), doc_id=doc_id
    )
    job_id: str | None = None
    if job is not None:
        raw_id = getattr(job, "job_id", None)
        if isinstance(raw_id, str):
            job_id = raw_id
    body = SourceResponse(
        id=doc_id, title=title or filename, status="parsing", job_id=job_id
    )
    return JSONResponse(content=body.model_dump(), status_code=202)


@router.get(
    "/sources",
    response_model=list[SourceDetail],
    operation_id="listSources",
)
async def list_sources(
    db: Annotated[Database, Depends(get_db)],
) -> list[SourceRow]:
    return await db.list_sources()


@router.get(
    "/sources/{doc_id}",
    response_model=SourceDetail,
    operation_id="getSource",
)
async def get_source(
    doc_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> SourceRow:
    row = await db.get_source_row(doc_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return row


@router.get(
    "/sources/{doc_id}/file",
    operation_id="getSourceFile",
)
async def get_source_file(
    doc_id: str,
    db: Annotated[Database, Depends(get_db)],
) -> FileResponse:
    row = await db.get_source(doc_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Source not found")
    file_path = Path(row["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Source file not found on disk")
    filename = os.path.basename(file_path)
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename,
    )


@router.get(
    "/sources/{doc_id}/excerpt",
    response_model=ExcerptResponse,
    operation_id="getSourceExcerpt",
)
async def get_source_excerpt(
    doc_id: str,
    db: Annotated[Database, Depends(get_db)],
    cache: Annotated[dict[str, ParsedDocument], Depends(get_parsed_doc_cache)],
    char_start: Annotated[int, Query(ge=0)],
    char_end: Annotated[int, Query(ge=0)],
    radius: Annotated[int, Query(ge=1, le=2000)] = 200,
) -> ExcerptResponse:
    if doc_id not in cache:
        row = await db.get_source(doc_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Source not found")
        file_path = Path(row["path"])
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Source file not found on disk")
        if len(cache) >= 16:
            cache.pop(next(iter(cache)))
        from lyw_core.parser.docling import (
            DoclingParser,
        )  # lazy: avoid heavy import at module load

        cache[doc_id] = DoclingParser().parse(file_path)

    excerpt = extract_excerpt(cache[doc_id], char_start, char_end, radius=radius)
    return ExcerptResponse(
        text=excerpt.text,
        doc_id=doc_id,
        char_start=char_start,
        char_end=char_end,
        window_start=excerpt.window_start,
    )
