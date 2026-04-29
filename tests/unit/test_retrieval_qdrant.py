"""Unit tests for Qdrant dense retrieval (no external services)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from qdrant_client import QdrantClient
from qdrant_client.http.models import QueryResponse, ScoredPoint

from lesson_graph.models import ConceptNode, SourceSpan
from lyw_core.retrieval.embedding import VECTOR_DIM, EmbeddingModel
from lyw_core.retrieval.qdrant import QdrantIndexer, QdrantRetriever, _collection_name
from lyw_core.retrieval.types import Retriever


def _span(char_start: int, char_end: int) -> SourceSpan:
    return SourceSpan(
        doc_id="doc1",
        page_start=1,
        page_end=1,
        char_start=char_start,
        char_end=char_end,
    )


def _concept(cid: str, title: str) -> ConceptNode:
    return ConceptNode(
        id=cid,
        title=title,
        summary=f"Summary of {title}",
        learning_objective=f"Understand {title}",
        source_spans=[_span(0, 50)],
    )


def _scored_point(
    concept_id: str, score: float, span: SourceSpan, text: str
) -> ScoredPoint:
    return ScoredPoint(
        id=0,
        version=0,
        score=score,
        payload={
            "concept_id": concept_id,
            "source_span": span.model_dump(),
            "text": text,
        },
    )


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock(spec=QdrantClient)
    client.collection_exists.return_value = False
    return client


@pytest.fixture
def mock_embedding() -> MagicMock:
    emb = MagicMock(spec=EmbeddingModel)
    emb.encode.return_value = [[0.1] * VECTOR_DIM]
    return emb


# --- collection name ---


def test_collection_name_prefix() -> None:
    assert _collection_name("abc") == "lesson_abc"


def test_collection_name_preserves_id() -> None:
    assert _collection_name("bio-101") == "lesson_bio-101"


# --- EmbeddingModel ---


@patch("lyw_core.retrieval.embedding.SentenceTransformer")
def test_embedding_model_encode(mock_st_class: Any) -> None:
    mock_model = MagicMock()
    mock_model.encode.return_value = np.array([[0.1] * VECTOR_DIM, [0.2] * VECTOR_DIM])
    mock_st_class.return_value = mock_model

    model = EmbeddingModel()
    result = model.encode(["text1", "text2"])

    assert len(result) == 2
    assert len(result[0]) == VECTOR_DIM
    mock_model.encode.assert_called_once_with(["text1", "text2"], convert_to_numpy=True)


@patch("lyw_core.retrieval.embedding.SentenceTransformer")
def test_embedding_model_init_uses_pinned_model(mock_st_class: Any) -> None:
    EmbeddingModel()
    mock_st_class.assert_called_once_with("all-MiniLM-L6-v2")


# --- QdrantIndexer ---


def test_indexer_creates_collection_when_absent(
    mock_client: MagicMock, mock_embedding: MagicMock
) -> None:
    mock_client.collection_exists.return_value = False
    indexer = QdrantIndexer(client=mock_client, embedding=mock_embedding)
    indexer.index("lesson1", [_concept("c1", "Photosynthesis")])

    mock_client.delete_collection.assert_not_called()
    mock_client.create_collection.assert_called_once()


def test_indexer_replaces_existing_collection(
    mock_client: MagicMock, mock_embedding: MagicMock
) -> None:
    mock_client.collection_exists.return_value = True
    indexer = QdrantIndexer(client=mock_client, embedding=mock_embedding)
    indexer.index("lesson1", [_concept("c1", "Photosynthesis")])

    mock_client.delete_collection.assert_called_once_with("lesson_lesson1")
    mock_client.create_collection.assert_called_once()


def test_indexer_upserts_one_point_per_concept(
    mock_client: MagicMock, mock_embedding: MagicMock
) -> None:
    concepts = [_concept("c1", "A"), _concept("c2", "B"), _concept("c3", "C")]
    mock_embedding.encode.return_value = [[0.1] * VECTOR_DIM] * 3
    indexer = QdrantIndexer(client=mock_client, embedding=mock_embedding)
    indexer.index("lesson1", concepts)

    call_kwargs = mock_client.upsert.call_args
    points = call_kwargs.kwargs["points"]
    assert len(points) == 3
    assert {p.payload["concept_id"] for p in points} == {"c1", "c2", "c3"}


def test_indexer_uses_namespaced_collection(
    mock_client: MagicMock, mock_embedding: MagicMock
) -> None:
    indexer = QdrantIndexer(client=mock_client, embedding=mock_embedding)
    indexer.index("bio101", [_concept("c1", "Cell")])

    name = mock_client.create_collection.call_args.kwargs["collection_name"]
    assert name == "lesson_bio101"


# --- QdrantRetriever ---


def test_retriever_protocol_compliance(
    mock_client: MagicMock, mock_embedding: MagicMock
) -> None:
    retriever = QdrantRetriever(
        client=mock_client, embedding=mock_embedding, lesson_id="l1"
    )
    _: Retriever = retriever


def test_retriever_returns_hits(
    mock_client: MagicMock, mock_embedding: MagicMock
) -> None:
    span = _span(0, 50)
    mock_client.query_points.return_value = QueryResponse(
        points=[_scored_point("c1", 0.9, span, "some text")]
    )
    retriever = QdrantRetriever(
        client=mock_client, embedding=mock_embedding, lesson_id="l1"
    )
    hits = retriever.retrieve("query", top_k=3)

    assert len(hits) == 1
    assert hits[0].concept_id == "c1"
    assert hits[0].score == pytest.approx(0.9)
    assert isinstance(hits[0].source_span, SourceSpan)


def test_retriever_passes_top_k(
    mock_client: MagicMock, mock_embedding: MagicMock
) -> None:
    mock_client.query_points.return_value = QueryResponse(points=[])
    retriever = QdrantRetriever(
        client=mock_client, embedding=mock_embedding, lesson_id="l1"
    )
    retriever.retrieve("query", top_k=7)

    call_kwargs = mock_client.query_points.call_args.kwargs
    assert call_kwargs["limit"] == 7


def test_retriever_uses_namespaced_collection(
    mock_client: MagicMock, mock_embedding: MagicMock
) -> None:
    mock_client.query_points.return_value = QueryResponse(points=[])
    retriever = QdrantRetriever(
        client=mock_client, embedding=mock_embedding, lesson_id="bio101"
    )
    retriever.retrieve("query")

    name = mock_client.query_points.call_args.kwargs["collection_name"]
    assert name == "lesson_bio101"


def test_retriever_handles_empty_payload(
    mock_client: MagicMock, mock_embedding: MagicMock
) -> None:
    point = ScoredPoint(id=0, version=0, score=0.5, payload=None)
    mock_client.query_points.return_value = QueryResponse(points=[point])
    retriever = QdrantRetriever(
        client=mock_client, embedding=mock_embedding, lesson_id="l1"
    )
    with pytest.raises((KeyError, TypeError)):
        retriever.retrieve("query")
