"""Unit tests for the ingest job - no Docker required."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lesson_graph.models import ConceptNode, LessonGraph, SourceSpan


def _make_concept(cid: str = "c1") -> ConceptNode:
    return ConceptNode(
        id=cid,
        title="Test Concept",
        summary="A test concept",
        learning_objective="Understand testing",
        source_spans=[
            SourceSpan(
                doc_id="doc1",
                page_start=1,
                page_end=1,
                char_start=0,
                char_end=10,
            )
        ],
    )


@pytest.fixture
def fake_ctx() -> dict[str, Any]:
    return {
        "db": AsyncMock(),
        "bm25_retriever": MagicMock(),
        "qdrant_client": MagicMock(),
        "embedding": MagicMock(),
    }


@pytest.mark.asyncio
async def test_returns_lesson_id_and_count(
    fake_ctx: dict[str, Any], tmp_path: Path
) -> None:
    from lyw_core.worker.jobs.ingest import ingest_source

    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    concepts = [_make_concept("c1"), _make_concept("c2")]

    with (
        patch("lyw_core.worker.jobs.ingest.DoclingParser") as mock_parser,
        patch("lyw_core.worker.jobs.ingest.HeuristicChunker") as mock_chunker,
        patch("lyw_core.worker.jobs.ingest.QdrantIndexer"),
    ):
        mock_parser.return_value.parse.return_value = MagicMock()
        mock_chunker.return_value.chunk.return_value = concepts

        result = await ingest_source(fake_ctx, source_path=str(pdf), doc_id="doc1")

    assert result["lesson_id"] == "lesson_doc1"
    assert result["concept_count"] == 2


@pytest.mark.asyncio
async def test_persists_lesson_graph(fake_ctx: dict[str, Any], tmp_path: Path) -> None:
    from lyw_core.worker.jobs.ingest import ingest_source

    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    concepts = [_make_concept()]

    with (
        patch("lyw_core.worker.jobs.ingest.DoclingParser") as mock_parser,
        patch("lyw_core.worker.jobs.ingest.HeuristicChunker") as mock_chunker,
        patch("lyw_core.worker.jobs.ingest.QdrantIndexer"),
    ):
        mock_parser.return_value.parse.return_value = MagicMock()
        mock_chunker.return_value.chunk.return_value = concepts

        await ingest_source(fake_ctx, source_path=str(pdf), doc_id="doc1")

    db: AsyncMock = fake_ctx["db"]
    db.upsert_lesson_graph.assert_awaited_once()
    graph: LessonGraph = db.upsert_lesson_graph.call_args[0][0]
    assert isinstance(graph, LessonGraph)
    assert graph.id == "lesson_doc1"
    assert graph.source_id == "doc1"
    assert graph.concepts == concepts


@pytest.mark.asyncio
async def test_indexes_bm25(fake_ctx: dict[str, Any], tmp_path: Path) -> None:
    from lyw_core.worker.jobs.ingest import ingest_source

    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    concepts = [_make_concept()]

    with (
        patch("lyw_core.worker.jobs.ingest.DoclingParser") as mock_parser,
        patch("lyw_core.worker.jobs.ingest.HeuristicChunker") as mock_chunker,
        patch("lyw_core.worker.jobs.ingest.QdrantIndexer"),
    ):
        mock_parser.return_value.parse.return_value = MagicMock()
        mock_chunker.return_value.chunk.return_value = concepts

        await ingest_source(fake_ctx, source_path=str(pdf), doc_id="doc1")

    fake_ctx["bm25_retriever"].index.assert_called_once_with(concepts)


@pytest.mark.asyncio
async def test_indexes_qdrant(fake_ctx: dict[str, Any], tmp_path: Path) -> None:
    from lyw_core.worker.jobs.ingest import ingest_source

    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    concepts = [_make_concept()]

    with (
        patch("lyw_core.worker.jobs.ingest.DoclingParser") as mock_parser,
        patch("lyw_core.worker.jobs.ingest.HeuristicChunker") as mock_chunker,
        patch("lyw_core.worker.jobs.ingest.QdrantIndexer") as mock_indexer,
    ):
        mock_parser.return_value.parse.return_value = MagicMock()
        mock_chunker.return_value.chunk.return_value = concepts

        await ingest_source(fake_ctx, source_path=str(pdf), doc_id="doc1")

    mock_indexer.assert_called_once_with(
        client=fake_ctx["qdrant_client"],
        embedding=fake_ctx["embedding"],
    )
    mock_indexer.return_value.index.assert_called_once_with("lesson_doc1", concepts)


@pytest.mark.asyncio
async def test_shutdown_closes_db() -> None:
    from lyw_core.worker.jobs.ingest import shutdown

    db = AsyncMock()
    await shutdown({"db": db})
    db.close.assert_awaited_once()


def _make_concept_no_spans(cid: str = "c_no_spans") -> ConceptNode:
    """Create a ConceptNode with no source_spans by bypassing Pydantic validation."""
    concept = ConceptNode.model_construct(
        id=cid,
        title="Spanless Concept",
        summary="A concept with no source spans",
        learning_objective="Understand nothing",
        source_spans=[],
        prerequisites=[],
        provenance="heuristic",
        temporal_position=None,
    )
    return concept


@pytest.mark.asyncio
async def test_ingest_drops_concepts_with_no_source_spans(
    fake_ctx: dict[str, Any], tmp_path: Path
) -> None:
    """Concepts with empty source_spans are dropped before upsert."""
    from lyw_core.worker.jobs.ingest import ingest_source

    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    good_concept = _make_concept("c1")
    bad_concept = _make_concept_no_spans("c_bad")
    concepts = [good_concept, bad_concept]

    with (
        patch("lyw_core.worker.jobs.ingest.DoclingParser") as mock_parser,
        patch("lyw_core.worker.jobs.ingest.HeuristicChunker") as mock_chunker,
        patch("lyw_core.worker.jobs.ingest.QdrantIndexer"),
    ):
        mock_parser.return_value.parse.return_value = MagicMock()
        mock_chunker.return_value.chunk.return_value = concepts

        result = await ingest_source(fake_ctx, source_path=str(pdf), doc_id="doc1")

    # Only the good concept reaches the store
    db: AsyncMock = fake_ctx["db"]
    db.upsert_lesson_graph.assert_awaited_once()
    graph: LessonGraph = db.upsert_lesson_graph.call_args[0][0]
    assert len(graph.concepts) == 1
    assert graph.concepts[0].id == "c1"
    # concept count reflects the filtered count
    assert result["concept_count"] == 1


@pytest.mark.asyncio
async def test_ingest_all_concepts_dropped_produces_empty_graph(
    fake_ctx: dict[str, Any], tmp_path: Path
) -> None:
    """If all concepts have no source_spans, the graph is stored with 0 concepts."""
    from lyw_core.worker.jobs.ingest import ingest_source

    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    bad_concepts = [_make_concept_no_spans("c1"), _make_concept_no_spans("c2")]

    with (
        patch("lyw_core.worker.jobs.ingest.DoclingParser") as mock_parser,
        patch("lyw_core.worker.jobs.ingest.HeuristicChunker") as mock_chunker,
        patch("lyw_core.worker.jobs.ingest.QdrantIndexer"),
    ):
        mock_parser.return_value.parse.return_value = MagicMock()
        mock_chunker.return_value.chunk.return_value = bad_concepts

        result = await ingest_source(fake_ctx, source_path=str(pdf), doc_id="doc1")

    db: AsyncMock = fake_ctx["db"]
    graph: LessonGraph = db.upsert_lesson_graph.call_args[0][0]
    assert graph.concepts == []
    assert result["concept_count"] == 0


@pytest.mark.asyncio
async def test_shutdown_no_db_key_does_not_raise() -> None:
    """Shutdown must not raise KeyError when startup failed before db was set."""
    from lyw_core.worker.jobs.ingest import shutdown

    # ctx has no "db" key — simulates a partially-initialized context
    await shutdown({})


@pytest.mark.asyncio
async def test_startup_bootstraps_data_dir(tmp_path: Path) -> None:
    """startup() must call DataDir.bootstrap() before Database.connect()."""
    from lyw_core.worker.jobs.ingest import startup

    mock_db = AsyncMock()
    mock_data_dir = MagicMock()

    with (
        patch(
            "lyw_core.worker.jobs.ingest.Settings",
            return_value=MagicMock(
                db_path=tmp_path / "lyw.db",
                data_dir=tmp_path,
                qdrant_url="http://localhost:6333",
            ),
        ),
        patch(
            "lyw_core.worker.jobs.ingest.DataDir",
            return_value=mock_data_dir,
        ) as mock_data_dir_cls,
        patch(
            "lyw_core.worker.jobs.ingest.Database.connect",
            new_callable=AsyncMock,
            return_value=mock_db,
        ),
        patch("lyw_core.worker.jobs.ingest.QdrantClient"),
        patch("lyw_core.worker.jobs.ingest.EmbeddingModel"),
        patch("lyw_core.worker.jobs.ingest.BM25Retriever"),
    ):
        ctx: dict[str, Any] = {}
        await startup(ctx)

    mock_data_dir_cls.assert_called_once()
    mock_data_dir.bootstrap.assert_called_once()
    assert ctx["db"] is mock_db
