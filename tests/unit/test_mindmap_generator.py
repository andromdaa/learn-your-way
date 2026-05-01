"""Unit tests for MindMapGenerator (pure logic, no model calls)."""

from __future__ import annotations

import pytest

from lesson_graph.models import (
    ConceptNode,
    LessonGraph,
    PersonalizationProfile,
    SourceSpan,
)
from lyw_core.modalities.mindmap import MindMapGenerator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _span() -> SourceSpan:
    return SourceSpan(
        doc_id="doc-1", page_start=1, page_end=2, char_start=0, char_end=100
    )


def _concept(
    cid: str, title: str, prerequisites: list[str] | None = None
) -> ConceptNode:
    return ConceptNode(
        id=cid,
        title=title,
        summary=f"Summary for {cid}.",
        learning_objective=f"Understand {cid}.",
        source_spans=[_span()],
        prerequisites=prerequisites or [],
    )


def _profile() -> PersonalizationProfile:
    return PersonalizationProfile(grade_level="8", interests=["space"])


def _graph(concepts: list[ConceptNode]) -> LessonGraph:
    return LessonGraph(id="g1", source_id="doc-1", concepts=concepts)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_basic_graph_produces_valid_mermaid() -> None:
    concepts = [
        _concept("c1", "Roots"),
        _concept("c2", "Stems", ["c1"]),
        _concept("c3", "Leaves", ["c1", "c2"]),
    ]
    out = MindMapGenerator().generate(_graph(concepts), _profile())

    assert out.startswith("flowchart TD\n")
    # Every concept appears as a node.
    assert 'c1["Roots"]' in out
    assert 'c2["Stems"]' in out
    assert 'c3["Leaves"]' in out
    # Edges go prereq --> dependent.
    assert "c1 --> c2" in out
    assert "c1 --> c3" in out
    assert "c2 --> c3" in out


def test_pruning_respects_max_nodes() -> None:
    # 10-concept chain c0 <- c1 <- c2 <- ... <- c9 (each depends on previous).
    concepts = [_concept("c0", "Concept 0")]
    for i in range(1, 10):
        concepts.append(_concept(f"c{i}", f"Concept {i}", [f"c{i - 1}"]))

    out = MindMapGenerator().generate(_graph(concepts), _profile(), max_nodes=3)

    # Each node line contains `["` exactly once; count occurrences.
    assert out.count('["') <= 3


def test_focal_concept_override() -> None:
    concepts = [
        _concept("c1", "Root concept"),
        _concept("c2", "Branch", ["c1"]),
        _concept("c3", "Leaf alpha", ["c2"]),
        _concept("c4", "Leaf beta", ["c2"]),
    ]
    # Force focal=c3; c4 is not reachable from c3 via prerequisites.
    out = MindMapGenerator().generate(
        _graph(concepts), _profile(), focal_concept_id="c3"
    )

    assert 'c3["Leaf alpha"]' in out
    # c4 is not reachable from c3 via prerequisites, so it must be absent.
    assert 'c4["Leaf beta"]' not in out


def test_focal_concept_unknown_raises() -> None:
    concepts = [_concept("c1", "Only")]
    with pytest.raises(ValueError, match="focal_concept_id"):
        MindMapGenerator().generate(
            _graph(concepts), _profile(), focal_concept_id="missing"
        )


def test_empty_lesson_graph_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        MindMapGenerator().generate(_graph([]), _profile())


def test_cycle_in_prerequisites_does_not_loop() -> None:
    # c1 -> c2 -> c1 cycle (allowed by schema; generator must guard).
    concepts = [
        _concept("c1", "Alpha", ["c2"]),
        _concept("c2", "Beta", ["c1"]),
    ]
    out = MindMapGenerator().generate(_graph(concepts), _profile())
    assert out.count('["') == 2


def test_node_id_sanitization() -> None:
    # ConceptNode.id values can contain dashes/dots; Mermaid requires alnum/_.
    concepts = [
        _concept("c-1.alpha", "Alpha"),
        _concept("c-2.beta", "Beta", ["c-1.alpha"]),
    ]
    out = MindMapGenerator().generate(_graph(concepts), _profile())
    assert "c_1_alpha" in out
    assert "c_2_beta" in out
    assert "c_1_alpha --> c_2_beta" in out


def test_no_model_calls_needed() -> None:
    """Regression guard: generator must require no model client.

    If this test ever needs a mock, the generator has drifted from the
    pure-logic contract in T1.
    """
    concepts = [_concept("c1", "Solo"), _concept("c2", "Pair", ["c1"])]
    out = MindMapGenerator().generate(_graph(concepts), _profile())
    assert out.startswith("flowchart TD")
