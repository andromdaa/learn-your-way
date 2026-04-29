"""Unit tests for CrossEncoderReranker (no model downloads)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from lesson_graph.models import SourceSpan
from lyw_core.retrieval.reranker import CROSS_ENCODER_MODEL, CrossEncoderReranker
from lyw_core.retrieval.types import RetrievalHit


def _span() -> SourceSpan:
    return SourceSpan(
        doc_id="doc1", page_start=1, page_end=1, char_start=0, char_end=50
    )


def _hit(concept_id: str, score: float, text: str) -> RetrievalHit:
    return RetrievalHit(
        concept_id=concept_id,
        score=score,
        source_span=_span(),
        text=text,
    )


@pytest.fixture
def mock_cross_encoder() -> MagicMock:
    model = MagicMock()
    # predict returns a numpy array of scores, one per pair
    model.predict.return_value = np.array([0.9, 0.3, 0.6])
    return model


def test_model_name_constant() -> None:
    assert CROSS_ENCODER_MODEL == "ms-marco-MiniLM-L-6-v2"


def test_rerank_returns_top_k(mock_cross_encoder: MagicMock) -> None:
    reranker = CrossEncoderReranker(model=mock_cross_encoder)
    hits = [
        _hit("c1", 1.0, "text1"),
        _hit("c2", 0.5, "text2"),
        _hit("c3", 0.2, "text3"),
    ]
    result = reranker.rerank("query", hits, top_k=2)
    assert len(result) == 2


def test_rerank_orders_by_cross_encoder_score(mock_cross_encoder: MagicMock) -> None:
    # scores: c1=0.9, c2=0.3, c3=0.6 → expected order: c1, c3, c2
    reranker = CrossEncoderReranker(model=mock_cross_encoder)
    hits = [
        _hit("c1", 1.0, "text1"),
        _hit("c2", 0.5, "text2"),
        _hit("c3", 0.2, "text3"),
    ]
    result = reranker.rerank("query", hits, top_k=3)
    assert [h.concept_id for h in result] == ["c1", "c3", "c2"]


def test_rerank_updates_scores_from_cross_encoder(
    mock_cross_encoder: MagicMock,
) -> None:
    reranker = CrossEncoderReranker(model=mock_cross_encoder)
    hits = [
        _hit("c1", 1.0, "text1"),
        _hit("c2", 0.5, "text2"),
        _hit("c3", 0.2, "text3"),
    ]
    result = reranker.rerank("query", hits, top_k=3)
    # scores should be cross-encoder scores, not original BM25/dense scores
    assert result[0].score == pytest.approx(0.9)
    assert result[1].score == pytest.approx(0.6)
    assert result[2].score == pytest.approx(0.3)


def test_rerank_preserves_source_span(mock_cross_encoder: MagicMock) -> None:
    reranker = CrossEncoderReranker(model=mock_cross_encoder)
    hits = [
        _hit("c1", 1.0, "text1"),
        _hit("c2", 0.5, "text2"),
        _hit("c3", 0.2, "text3"),
    ]
    result = reranker.rerank("query", hits, top_k=3)
    for hit in result:
        assert isinstance(hit.source_span, SourceSpan)


def test_rerank_empty_hits(mock_cross_encoder: MagicMock) -> None:
    reranker = CrossEncoderReranker(model=mock_cross_encoder)
    result = reranker.rerank("query", [], top_k=5)
    assert result == []
    mock_cross_encoder.predict.assert_not_called()


def test_rerank_top_k_larger_than_hits(mock_cross_encoder: MagicMock) -> None:
    mock_cross_encoder.predict.return_value = np.array([0.7, 0.4])
    reranker = CrossEncoderReranker(model=mock_cross_encoder)
    hits = [_hit("c1", 1.0, "text1"), _hit("c2", 0.5, "text2")]
    result = reranker.rerank("query", hits, top_k=10)
    assert len(result) == 2


def test_rerank_stable_run_to_run(mock_cross_encoder: MagicMock) -> None:
    reranker = CrossEncoderReranker(model=mock_cross_encoder)
    hits = [
        _hit("c1", 1.0, "text1"),
        _hit("c2", 0.5, "text2"),
        _hit("c3", 0.2, "text3"),
    ]
    result_a = reranker.rerank("query", hits, top_k=3)
    mock_cross_encoder.predict.return_value = np.array([0.9, 0.3, 0.6])
    result_b = reranker.rerank("query", hits, top_k=3)
    assert [h.concept_id for h in result_a] == [h.concept_id for h in result_b]


def test_rerank_calls_predict_with_pairs(mock_cross_encoder: MagicMock) -> None:
    reranker = CrossEncoderReranker(model=mock_cross_encoder)
    hits = [_hit("c1", 1.0, "alpha"), _hit("c2", 0.5, "beta"), _hit("c3", 0.2, "gamma")]
    reranker.rerank("my query", hits, top_k=3)
    pairs = mock_cross_encoder.predict.call_args[0][0]
    assert pairs == [["my query", "alpha"], ["my query", "beta"], ["my query", "gamma"]]


@patch("lyw_core.retrieval.reranker.CrossEncoder")
def test_default_constructor_loads_pinned_model(mock_ce_class: Any) -> None:
    mock_ce_class.return_value = MagicMock()
    CrossEncoderReranker()
    mock_ce_class.assert_called_once_with(CROSS_ENCODER_MODEL)
