"""Unit tests for TimelineGenerator (pure logic, no model calls)."""

from __future__ import annotations

import pytest
from syrupy.assertion import SnapshotAssertion

from lesson_graph.models import (
    ConceptNode,
    LessonGraph,
    PersonalizationProfile,
    SourceSpan,
)
from lyw_core.modalities.timeline import TimelineGenerator, TimelineResult, TimelineSkipped

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _span() -> SourceSpan:
    return SourceSpan(
        doc_id="doc-1", page_start=1, page_end=2, char_start=0, char_end=100
    )


def _concept(
    cid: str,
    title: str,
    temporal_position: int | None = None,
    prerequisites: list[str] | None = None,
) -> ConceptNode:
    return ConceptNode(
        id=cid,
        title=title,
        summary=f"Summary for {cid}.",
        learning_objective=f"Understand {cid}.",
        source_spans=[_span()],
        prerequisites=prerequisites or [],
        temporal_position=temporal_position,
    )


def _profile() -> PersonalizationProfile:
    return PersonalizationProfile(grade_level="8", interests=["history"])


def _graph(concepts: list[ConceptNode]) -> LessonGraph:
    return LessonGraph(id="g1", source_id="doc-1", concepts=concepts)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_all_concepts_with_temporal_position_produces_result() -> None:
    """A graph where every concept has temporal_position returns TimelineResult."""
    concepts = [
        _concept("c1", "The Big Bang", temporal_position=1),
        _concept("c2", "Formation of Stars", temporal_position=2),
        _concept("c3", "First Life", temporal_position=3),
    ]
    result = TimelineGenerator().generate(_graph(concepts), _profile())

    assert isinstance(result, TimelineResult)
    assert result.mermaid.startswith("timeline\n")
    assert "The Big Bang" in result.mermaid
    assert "Formation of Stars" in result.mermaid
    assert "First Life" in result.mermaid


def test_no_temporal_position_returns_skipped() -> None:
    """A graph where no concept has temporal_position returns TimelineSkipped."""
    concepts = [
        _concept("c1", "Alpha"),
        _concept("c2", "Beta"),
    ]
    result = TimelineGenerator().generate(_graph(concepts), _profile())

    assert isinstance(result, TimelineSkipped)


def test_partial_temporal_position_includes_only_positioned_concepts() -> None:
    """Only concepts with temporal_position set appear in the timeline."""
    concepts = [
        _concept("c1", "Positioned", temporal_position=5),
        _concept("c2", "Not Positioned"),
        _concept("c3", "Also Positioned", temporal_position=10),
    ]
    result = TimelineGenerator().generate(_graph(concepts), _profile())

    assert isinstance(result, TimelineResult)
    assert "Positioned" in result.mermaid
    assert "Also Positioned" in result.mermaid
    assert "Not Positioned" not in result.mermaid
    assert result.concept_ids == ["c1", "c3"]


def test_ascending_order_by_temporal_position() -> None:
    """Concepts are sorted ascending by temporal_position in the output."""
    concepts = [
        _concept("c3", "Third", temporal_position=30),
        _concept("c1", "First", temporal_position=10),
        _concept("c2", "Second", temporal_position=20),
    ]
    result = TimelineGenerator().generate(_graph(concepts), _profile())

    assert isinstance(result, TimelineResult)
    mermaid = result.mermaid
    idx_first = mermaid.index("First")
    idx_second = mermaid.index("Second")
    idx_third = mermaid.index("Third")
    assert idx_first < idx_second < idx_third


def test_result_concept_ids_match_positioned_concepts() -> None:
    """TimelineResult.concept_ids contains only concepts with temporal_position."""
    concepts = [
        _concept("c1", "Alpha", temporal_position=1),
        _concept("c2", "Beta"),
        _concept("c3", "Gamma", temporal_position=3),
    ]
    result = TimelineGenerator().generate(_graph(concepts), _profile())

    assert isinstance(result, TimelineResult)
    assert set(result.concept_ids) == {"c1", "c3"}


def test_negative_temporal_position_valid() -> None:
    """Negative temporal_position values (BC dates / pre-epoch) are supported."""
    concepts = [
        _concept("c1", "Primordial", temporal_position=-100),
        _concept("c2", "Ancient", temporal_position=-50),
        _concept("c3", "Recent", temporal_position=1),
    ]
    result = TimelineGenerator().generate(_graph(concepts), _profile())

    assert isinstance(result, TimelineResult)
    mermaid = result.mermaid
    idx_primordial = mermaid.index("Primordial")
    idx_ancient = mermaid.index("Ancient")
    idx_recent = mermaid.index("Recent")
    assert idx_primordial < idx_ancient < idx_recent


def test_no_model_calls_needed() -> None:
    """Regression guard: generator must require no model client."""
    concepts = [
        _concept("c1", "Event One", temporal_position=1),
        _concept("c2", "Event Two", temporal_position=2),
    ]
    result = TimelineGenerator().generate(_graph(concepts), _profile())
    assert isinstance(result, TimelineResult)
    assert result.mermaid.startswith("timeline")


def test_mermaid_output_has_section_per_concept() -> None:
    """Each positioned concept appears as a section in the timeline."""
    concepts = [
        _concept("c1", "Dawn of Time", temporal_position=1),
        _concept("c2", "Iron Age", temporal_position=2),
    ]
    result = TimelineGenerator().generate(_graph(concepts), _profile())

    assert isinstance(result, TimelineResult)
    assert "section" in result.mermaid


def test_snapshot_output_shape(snapshot: SnapshotAssertion) -> None:
    concepts = [
        _concept("c1", "Big Bang", temporal_position=1),
        _concept("c2", "Star Formation", temporal_position=2),
        _concept("c3", "Solar System", temporal_position=3),
    ]
    result = TimelineGenerator().generate(_graph(concepts), _profile())
    assert isinstance(result, TimelineResult)
    assert snapshot == result.mermaid
