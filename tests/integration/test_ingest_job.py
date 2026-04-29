"""Integration tests for the ingest job - requires Docker."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from qdrant_client import QdrantClient
from testcontainers.qdrant import QdrantContainer

from lyw_core.db.dao import Database
from lyw_core.retrieval.bm25 import BM25Retriever
from lyw_core.retrieval.embedding import EmbeddingModel

_FIXTURE_PDF = Path(__file__).parent.parent / "fixtures" / "tiny_test.pdf"


@pytest.fixture(scope="module")
def qdrant_client() -> Generator[QdrantClient, None, None]:
    try:
        with QdrantContainer() as container:
            url = (
                f"http://{container.get_container_host_ip()}"
                f":{container.get_exposed_port(6333)}"
            )
            yield QdrantClient(url=url)
    except Exception:
        pytest.skip("Docker not available")


@pytest.fixture(scope="module")
def embedding() -> EmbeddingModel:
    return EmbeddingModel()


@pytest.fixture
async def db(tmp_path: Path) -> Database:
    database = await Database.connect(str(tmp_path / "test.db"))
    return database


@pytest.fixture
def ctx(
    db: Database,
    qdrant_client: QdrantClient,
    embedding: EmbeddingModel,
) -> dict[str, Any]:
    return {
        "db": db,
        "bm25_retriever": BM25Retriever(),
        "qdrant_client": qdrant_client,
        "embedding": embedding,
    }


@pytest.mark.integration
async def test_ingest_persists_lesson(ctx: dict[str, Any]) -> None:
    from lyw_core.worker.jobs.ingest import ingest_source

    result = await ingest_source(ctx, source_path=str(_FIXTURE_PDF), doc_id="tiny_test")

    assert result["lesson_id"] == "lesson_tiny_test"
    assert result["concept_count"] > 0

    db: Database = ctx["db"]
    graph = await db.get_lesson_graph("lesson_tiny_test")
    assert graph is not None
    assert graph.source_id == "tiny_test"
    assert len(graph.concepts) > 0


@pytest.mark.integration
async def test_ingest_populates_bm25(ctx: dict[str, Any]) -> None:
    from lyw_core.worker.jobs.ingest import ingest_source

    await ingest_source(ctx, source_path=str(_FIXTURE_PDF), doc_id="bm25_test")

    bm25: BM25Retriever = ctx["bm25_retriever"]
    hits = bm25.retrieve("introduction concepts", top_k=3)
    assert len(hits) > 0
    assert all(h.score >= 0 for h in hits)


@pytest.mark.integration
async def test_ingest_populates_qdrant(
    ctx: dict[str, Any], qdrant_client: QdrantClient
) -> None:
    from lyw_core.worker.jobs.ingest import ingest_source

    await ingest_source(ctx, source_path=str(_FIXTURE_PDF), doc_id="qdrant_test")

    collections = {c.name for c in qdrant_client.get_collections().collections}
    assert "lesson_lesson_qdrant_test" in collections
