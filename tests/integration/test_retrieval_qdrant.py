"""Integration tests for Qdrant dense retrieval."""

from __future__ import annotations

import pytest
from qdrant_client import QdrantClient

from lesson_graph.models import ConceptNode, SourceSpan
from lyw_core.retrieval.embedding import EmbeddingModel
from lyw_core.retrieval.qdrant import QdrantIndexer, QdrantRetriever
from lyw_core.retrieval.types import RetrievalHit, Retriever


def _concept(
    cid: str,
    title: str,
    summary: str,
    char_start: int,
    char_end: int,
) -> ConceptNode:
    return ConceptNode(
        id=cid,
        title=title,
        summary=summary,
        learning_objective=f"Understand {title.lower()}",
        source_spans=[
            SourceSpan(
                doc_id="doc1",
                page_start=1,
                page_end=1,
                char_start=char_start,
                char_end=char_end,
            )
        ],
    )


_CONCEPTS = [
    _concept("c1", "Photosynthesis", "How plants make food from sunlight", 0, 50),
    _concept(
        "c2", "Cellular Respiration", "How cells generate ATP from glucose", 50, 100
    ),
    _concept(
        "c3",
        "DNA Replication",
        "Copying genetic material before cell division",
        100,
        150,
    ),
]


@pytest.fixture(scope="module")
def embedding() -> EmbeddingModel:
    return EmbeddingModel()


@pytest.fixture(scope="module")
def indexed_retriever(
    qdrant_client: QdrantClient, embedding: EmbeddingModel
) -> QdrantRetriever:
    indexer = QdrantIndexer(client=qdrant_client, embedding=embedding)
    indexer.index("bio101", _CONCEPTS)
    return QdrantRetriever(
        client=qdrant_client, embedding=embedding, lesson_id="bio101"
    )


@pytest.mark.integration
def test_retriever_protocol_compliance(indexed_retriever: QdrantRetriever) -> None:
    _: Retriever = indexed_retriever


@pytest.mark.integration
def test_top_k_limits_results(indexed_retriever: QdrantRetriever) -> None:
    hits = indexed_retriever.retrieve("photosynthesis plants sunlight", top_k=2)
    assert len(hits) <= 2


@pytest.mark.integration
def test_relevant_concept_ranks_first(indexed_retriever: QdrantRetriever) -> None:
    hits = indexed_retriever.retrieve("photosynthesis plants sunlight", top_k=3)
    assert len(hits) > 0
    assert hits[0].concept_id == "c1"


@pytest.mark.integration
def test_hit_carries_source_span(indexed_retriever: QdrantRetriever) -> None:
    hits = indexed_retriever.retrieve("DNA genetic replication", top_k=1)
    assert len(hits) == 1
    assert isinstance(hits[0], RetrievalHit)
    assert isinstance(hits[0].source_span, SourceSpan)


@pytest.mark.integration
def test_hit_score_between_zero_and_one(indexed_retriever: QdrantRetriever) -> None:
    hits = indexed_retriever.retrieve("photosynthesis", top_k=1)
    assert len(hits) == 1
    assert 0.0 <= hits[0].score <= 1.0


@pytest.mark.integration
def test_collection_namespaced_per_lesson(
    qdrant_client: QdrantClient, embedding: EmbeddingModel
) -> None:
    indexer = QdrantIndexer(client=qdrant_client, embedding=embedding)
    indexer.index("lesson_a", _CONCEPTS[:1])
    indexer.index("lesson_b", _CONCEPTS[1:2])
    collection_names = {c.name for c in qdrant_client.get_collections().collections}
    assert "lesson_lesson_a" in collection_names
    assert "lesson_lesson_b" in collection_names


@pytest.mark.integration
def test_reindex_replaces_collection(
    qdrant_client: QdrantClient, embedding: EmbeddingModel
) -> None:
    indexer = QdrantIndexer(client=qdrant_client, embedding=embedding)
    indexer.index("replace_test", _CONCEPTS)
    indexer.index("replace_test", _CONCEPTS[:1])
    retriever = QdrantRetriever(
        client=qdrant_client, embedding=embedding, lesson_id="replace_test"
    )
    hits = retriever.retrieve("photosynthesis", top_k=5)
    assert len(hits) == 1
