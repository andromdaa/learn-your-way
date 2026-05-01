"""Arq ingest job: parse → chunk → persist → index."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import structlog
from qdrant_client import QdrantClient

from lesson_graph.models import LessonGraph
from lyw_core.chunker.heuristic import HeuristicChunker
from lyw_core.db.dao import Database
from lyw_core.parser.docling import DoclingParser
from lyw_core.retrieval.bm25 import BM25Retriever
from lyw_core.retrieval.embedding import EmbeddingModel
from lyw_core.retrieval.qdrant import QdrantIndexer
from lyw_core.settings import Settings
from lyw_core.storage.fs import DataDir
from lyw_core.worker.jobs._progress import make_progress

log = structlog.get_logger()


async def startup(ctx: dict[str, Any]) -> None:
    cfg = Settings()
    data_dir = DataDir(cfg.data_dir)
    data_dir.bootstrap()
    ctx["db"] = await Database.connect(str(cfg.db_path))
    ctx["qdrant_client"] = QdrantClient(url=cfg.qdrant_url)
    ctx["embedding"] = EmbeddingModel()
    ctx["bm25_retriever"] = BM25Retriever()


async def shutdown(ctx: dict[str, Any]) -> None:
    if "db" in ctx:
        db: Database = ctx["db"]
        await db.close()


async def ingest_source(
    ctx: dict[str, Any],
    *,
    source_path: str,
    doc_id: str,
) -> dict[str, Any]:
    progress = make_progress(ctx)
    db: Database = ctx["db"]
    bm25: BM25Retriever = ctx["bm25_retriever"]
    qdrant_client: QdrantClient = ctx["qdrant_client"]
    embedding: EmbeddingModel = ctx["embedding"]

    await progress.emit(phase="parse_start", pct=0.0)

    if await db.get_source(doc_id) is None:
        sha256 = hashlib.sha256(Path(source_path).read_bytes()).hexdigest()
        await db.add_source(doc_id=doc_id, path=source_path, sha256=sha256)

    parsed = DoclingParser().parse(Path(source_path))
    await progress.emit(phase="parse_done", pct=0.2)

    raw_concepts = HeuristicChunker(doc_id=doc_id).chunk(parsed)

    # Source fidelity: every concept must trace to at least one source span.
    # Drop concepts with no source spans rather than persisting invalid data.
    concepts = []
    for concept in raw_concepts:
        if not concept.source_spans:
            log.warning(
                "ingest.concept_dropped_no_source_spans",
                concept_id=concept.id,
                concept_title=concept.title,
                doc_id=doc_id,
            )
        else:
            concepts.append(concept)
    await progress.emit(phase="chunk_done", pct=0.5)

    lesson_id = f"lesson_{doc_id}"
    graph = LessonGraph(id=lesson_id, source_id=doc_id, concepts=concepts)
    await db.upsert_lesson_graph(graph)

    bm25.index(concepts)
    await progress.emit(phase="index_bm25_done", pct=0.7)

    QdrantIndexer(client=qdrant_client, embedding=embedding).index(lesson_id, concepts)
    await progress.emit(phase="index_qdrant_done", pct=0.9)

    result = {"lesson_id": lesson_id, "concept_count": len(concepts)}
    return await progress.done(result)
