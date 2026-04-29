"""Unit tests for BM25 retrieval pipeline."""

import pytest

from lesson_graph.models import ConceptNode, SourceSpan
from lyw_core.parser.models import ParsedBlock, ParsedDocument
from lyw_core.parser.verifier import verify_spans
from lyw_core.retrieval.bm25 import BM25Retriever
from lyw_core.retrieval.types import RetrievalHit, Retriever

_DOC_TEXT = (
    "Photosynthesis is how plants make food from sunlight. "
    "Cellular respiration generates energy from glucose. "
    "DNA replication copies the genetic material before cell division."
)


def _span(doc_id: str, start: int, end: int) -> SourceSpan:
    return SourceSpan(
        doc_id=doc_id,
        page_start=1,
        page_end=1,
        char_start=start,
        char_end=end,
    )


def _parsed_doc() -> ParsedDocument:
    text = _DOC_TEXT
    return ParsedDocument(
        source_path="fixture.pdf",
        text=text,
        blocks=[
            ParsedBlock(
                block_id="b0",
                page_number=1,
                block_type="text",
                text=text,
                char_start=0,
                char_end=len(text),
            )
        ],
        page_count=1,
    )


@pytest.fixture
def three_concept_retriever() -> BM25Retriever:
    concepts = [
        ConceptNode(
            id="c1",
            title="Photosynthesis",
            summary="How plants make food from sunlight",
            learning_objective="Explain the process of photosynthesis",
            source_spans=[_span("doc1", 0, 53)],
        ),
        ConceptNode(
            id="c2",
            title="Cellular Respiration",
            summary="How cells generate energy from glucose",
            learning_objective="Describe the steps of cellular respiration",
            source_spans=[_span("doc1", 53, 103)],
        ),
        ConceptNode(
            id="c3",
            title="DNA Replication",
            summary="Copying genetic material before cell division",
            learning_objective="Explain DNA replication and its fidelity",
            source_spans=[_span("doc1", 103, len(_DOC_TEXT))],
        ),
    ]
    r = BM25Retriever()
    r.index(concepts)
    return r


def test_retriever_protocol_compliance(three_concept_retriever: BM25Retriever) -> None:
    _: Retriever = three_concept_retriever


def test_top_k_limits_results(three_concept_retriever: BM25Retriever) -> None:
    hits = three_concept_retriever.retrieve("photosynthesis plants sunlight", top_k=2)
    assert len(hits) <= 2


def test_relevant_concept_ranks_first(three_concept_retriever: BM25Retriever) -> None:
    hits = three_concept_retriever.retrieve("photosynthesis plants sunlight", top_k=3)
    assert len(hits) > 0
    assert hits[0].concept_id == "c1"


def test_results_stable_across_runs(three_concept_retriever: BM25Retriever) -> None:
    hits_a = three_concept_retriever.retrieve("energy glucose respiration", top_k=3)
    hits_b = three_concept_retriever.retrieve("energy glucose respiration", top_k=3)
    assert [h.concept_id for h in hits_a] == [h.concept_id for h in hits_b]


def test_hit_carries_source_span(three_concept_retriever: BM25Retriever) -> None:
    hits = three_concept_retriever.retrieve("DNA replication genetic", top_k=1)
    assert len(hits) == 1
    assert isinstance(hits[0], RetrievalHit)
    assert isinstance(hits[0].source_span, SourceSpan)


def test_hit_source_spans_pass_round_trip_verifier(
    three_concept_retriever: BM25Retriever,
) -> None:
    doc = _parsed_doc()
    hits = three_concept_retriever.retrieve("photosynthesis cellular DNA", top_k=3)
    spans = [h.source_span for h in hits]
    failures = verify_spans(doc, spans)
    assert failures == [], failures


def test_hit_score_positive(three_concept_retriever: BM25Retriever) -> None:
    hits = three_concept_retriever.retrieve("photosynthesis", top_k=1)
    assert len(hits) == 1
    assert hits[0].score > 0
