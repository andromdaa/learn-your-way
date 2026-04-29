"""Unit tests for HybridRetriever (mocked BM25, dense, and reranker)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lesson_graph.models import SourceSpan
from lyw_core.retrieval.hybrid import HybridRetriever
from lyw_core.retrieval.reranker import CrossEncoderReranker
from lyw_core.retrieval.types import RetrievalHit, Retriever


def _span(char_start: int = 0, char_end: int = 50) -> SourceSpan:
    return SourceSpan(
        doc_id="doc1",
        page_start=1,
        page_end=1,
        char_start=char_start,
        char_end=char_end,
    )


def _hit(concept_id: str, score: float, text: str = "text") -> RetrievalHit:
    return RetrievalHit(
        concept_id=concept_id,
        score=score,
        source_span=_span(),
        text=text,
    )


def _reranker_passthrough(hits: list[RetrievalHit], top_k: int) -> list[RetrievalHit]:
    """Return hits sorted by score descending, capped at top_k."""
    return sorted(hits, key=lambda h: h.score, reverse=True)[:top_k]


@pytest.fixture
def mock_bm25() -> MagicMock:
    r = MagicMock(spec=Retriever)
    r.retrieve.return_value = [_hit("c1", 1.0), _hit("c2", 0.8)]
    return r


@pytest.fixture
def mock_dense() -> MagicMock:
    r = MagicMock(spec=Retriever)
    r.retrieve.return_value = [_hit("c3", 0.9), _hit("c4", 0.7)]
    return r


@pytest.fixture
def mock_reranker() -> MagicMock:
    reranker = MagicMock(spec=CrossEncoderReranker)
    reranker.rerank.side_effect = lambda query, hits, top_k: _reranker_passthrough(
        hits, top_k
    )
    return reranker


def test_hybrid_retriever_protocol_compliance(
    mock_bm25: MagicMock, mock_dense: MagicMock, mock_reranker: MagicMock
) -> None:
    hybrid = HybridRetriever(bm25=mock_bm25, dense=mock_dense, reranker=mock_reranker)
    _: Retriever = hybrid


def test_retrieve_fans_out_to_both_retrievers(
    mock_bm25: MagicMock, mock_dense: MagicMock, mock_reranker: MagicMock
) -> None:
    hybrid = HybridRetriever(bm25=mock_bm25, dense=mock_dense, reranker=mock_reranker)
    hybrid.retrieve("query", top_k=3)
    mock_bm25.retrieve.assert_called_once()
    mock_dense.retrieve.assert_called_once()


def test_retrieve_passes_fetch_k_to_retrievers(
    mock_bm25: MagicMock, mock_dense: MagicMock, mock_reranker: MagicMock
) -> None:
    hybrid = HybridRetriever(
        bm25=mock_bm25, dense=mock_dense, reranker=mock_reranker, fetch_k=15
    )
    hybrid.retrieve("query", top_k=3)
    assert mock_bm25.retrieve.call_args.kwargs["top_k"] == 15
    assert mock_dense.retrieve.call_args.kwargs["top_k"] == 15


def test_retrieve_deduplicates_by_concept_id(
    mock_reranker: MagicMock,
) -> None:
    bm25 = MagicMock(spec=Retriever)
    dense = MagicMock(spec=Retriever)
    bm25.retrieve.return_value = [_hit("c1", 1.0), _hit("c2", 0.8)]
    # c1 appears in both — should be deduplicated
    dense.retrieve.return_value = [_hit("c1", 0.95), _hit("c3", 0.7)]

    seen_concept_ids: list[str] = []

    def capture_rerank(
        query: str, hits: list[RetrievalHit], top_k: int
    ) -> list[RetrievalHit]:
        seen_concept_ids.extend(h.concept_id for h in hits)
        return _reranker_passthrough(hits, top_k)

    mock_reranker.rerank.side_effect = capture_rerank

    hybrid = HybridRetriever(bm25=bm25, dense=dense, reranker=mock_reranker)
    hybrid.retrieve("query", top_k=5)

    assert seen_concept_ids.count("c1") == 1


def test_retrieve_bm25_hit_wins_on_duplicate(
    mock_reranker: MagicMock,
) -> None:
    """When the same concept appears in both retrievers, the BM25 hit is kept."""
    bm25 = MagicMock(spec=Retriever)
    dense = MagicMock(spec=Retriever)
    bm25_hit = _hit("c1", 1.0, "bm25 text")
    dense_hit = _hit("c1", 0.95, "dense text")
    bm25.retrieve.return_value = [bm25_hit]
    dense.retrieve.return_value = [dense_hit]

    captured: list[RetrievalHit] = []

    def capture_rerank(
        query: str, hits: list[RetrievalHit], top_k: int
    ) -> list[RetrievalHit]:
        captured.extend(hits)
        return hits[:top_k]

    mock_reranker.rerank.side_effect = capture_rerank

    hybrid = HybridRetriever(bm25=bm25, dense=dense, reranker=mock_reranker)
    hybrid.retrieve("query", top_k=5)

    c1_hits = [h for h in captured if h.concept_id == "c1"]
    assert len(c1_hits) == 1
    assert c1_hits[0].text == "bm25 text"


def test_retrieve_returns_top_k(
    mock_bm25: MagicMock, mock_dense: MagicMock, mock_reranker: MagicMock
) -> None:
    hybrid = HybridRetriever(bm25=mock_bm25, dense=mock_dense, reranker=mock_reranker)
    result = hybrid.retrieve("query", top_k=2)
    assert len(result) <= 2


def test_retrieve_hits_have_source_spans(
    mock_bm25: MagicMock, mock_dense: MagicMock, mock_reranker: MagicMock
) -> None:
    hybrid = HybridRetriever(bm25=mock_bm25, dense=mock_dense, reranker=mock_reranker)
    result = hybrid.retrieve("query", top_k=4)
    for hit in result:
        assert isinstance(hit.source_span, SourceSpan)


def test_retrieve_empty_results_from_both(mock_reranker: MagicMock) -> None:
    bm25 = MagicMock(spec=Retriever)
    dense = MagicMock(spec=Retriever)
    bm25.retrieve.return_value = []
    dense.retrieve.return_value = []
    mock_reranker.rerank.return_value = []

    hybrid = HybridRetriever(bm25=bm25, dense=dense, reranker=mock_reranker)
    result = hybrid.retrieve("query", top_k=5)
    assert result == []


def test_retrieve_calls_reranker_with_query(
    mock_bm25: MagicMock, mock_dense: MagicMock, mock_reranker: MagicMock
) -> None:
    hybrid = HybridRetriever(bm25=mock_bm25, dense=mock_dense, reranker=mock_reranker)
    hybrid.retrieve("photosynthesis", top_k=3)
    call_args = mock_reranker.rerank.call_args
    assert (
        call_args.kwargs.get("query") == "photosynthesis"
        or call_args.args[0] == "photosynthesis"
    )


def test_retrieve_default_top_k(
    mock_bm25: MagicMock, mock_dense: MagicMock, mock_reranker: MagicMock
) -> None:
    hybrid = HybridRetriever(bm25=mock_bm25, dense=mock_dense, reranker=mock_reranker)
    hybrid.retrieve("query")
    call_args = mock_reranker.rerank.call_args
    top_k = call_args.kwargs.get("top_k") or call_args.args[2]
    assert top_k == 5
