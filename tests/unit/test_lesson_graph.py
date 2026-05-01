"""Tests for the canonical lesson graph schema.

These tests exercise the invariants documented in
docs/02-data-model.md. They do not test ingest or generation logic;
those belong with their respective phase implementations.
"""

import pytest
from pydantic import ValidationError

from lesson_graph import (
    ConceptNode,
    DerivedAsset,
    LessonGraph,
    PersonalizationProfile,
    ReplacementRecord,
    SourceSpan,
)


def _span(doc_id: str = "doc-1") -> SourceSpan:
    return SourceSpan(
        doc_id=doc_id,
        page_start=1,
        page_end=1,
        char_start=0,
        char_end=100,
    )


# SourceSpan ----------------------------------------------------------------


def test_source_span_valid() -> None:
    span = _span()
    assert span.char_end >= span.char_start
    assert span.page_end >= span.page_start


def test_source_span_rejects_inverted_pages() -> None:
    with pytest.raises(ValidationError):
        SourceSpan(doc_id="d", page_start=5, page_end=2, char_start=0, char_end=10)


def test_source_span_rejects_inverted_chars() -> None:
    with pytest.raises(ValidationError):
        SourceSpan(doc_id="d", page_start=1, page_end=1, char_start=50, char_end=10)


def test_source_span_rejects_negative_offsets() -> None:
    with pytest.raises(ValidationError):
        SourceSpan(doc_id="d", page_start=1, page_end=1, char_start=-1, char_end=10)


def test_source_span_validator_does_not_depend_on_field_order() -> None:
    """Cross-field validation must work via model_validator(mode='after').

    The earlier implementation used field_validator with info.data
    lookup, which silently passed if field declaration order changed.
    This test pins that down by submitting the cross-field-invalid
    pair through model_validate (dict input, no positional ordering).
    """
    with pytest.raises(ValidationError):
        SourceSpan.model_validate(
            {
                "doc_id": "d",
                "char_end": 10,
                "char_start": 50,
                "page_end": 1,
                "page_start": 1,
            }
        )
    with pytest.raises(ValidationError):
        SourceSpan.model_validate(
            {
                "doc_id": "d",
                "page_end": 2,
                "page_start": 5,
                "char_start": 0,
                "char_end": 10,
            }
        )


# ConceptNode ---------------------------------------------------------------


def test_concept_node_valid() -> None:
    node = ConceptNode(
        id="c1",
        title="Photosynthesis",
        summary="Plants make food from sunlight.",
        learning_objective="Explain how plants convert light into energy.",
        source_spans=[_span()],
    )
    assert len(node.source_spans) == 1
    assert node.prerequisites == []


def test_concept_node_requires_at_least_one_span() -> None:
    with pytest.raises(ValidationError):
        ConceptNode(
            id="c1",
            title="t",
            summary="s",
            learning_objective="lo",
            source_spans=[],
        )


def test_concept_node_provenance_defaults_to_heuristic() -> None:
    node = ConceptNode(
        id="c1",
        title="t",
        summary="s",
        learning_objective="lo",
        source_spans=[_span()],
    )
    assert node.provenance == "heuristic"


def test_concept_node_provenance_accepts_llm_refined() -> None:
    node = ConceptNode(
        id="c1",
        title="t",
        summary="s",
        learning_objective="lo",
        source_spans=[_span()],
        provenance="llm_refined",
    )
    assert node.provenance == "llm_refined"


def test_concept_node_provenance_rejects_invalid() -> None:
    with pytest.raises(ValidationError):
        ConceptNode(
            id="c1",
            title="t",
            summary="s",
            learning_objective="lo",
            source_spans=[_span()],
            provenance="unknown",
        )


def test_concept_node_does_not_serialise_temporal_position() -> None:
    """temporal_position was removed per ADR-0016; it must not be a field."""
    node = ConceptNode(
        id="c1",
        title="t",
        summary="s",
        learning_objective="lo",
        source_spans=[_span()],
    )
    assert "temporal_position" not in node.model_dump()


# DerivedAsset --------------------------------------------------------------


def _profile() -> PersonalizationProfile:
    return PersonalizationProfile(grade_level="8", interests=[])


def test_derived_asset_valid() -> None:
    asset = DerivedAsset(
        id="a1",
        kind="immersive_text",
        based_on_concepts=["c1"],
        personalization_profile=_profile(),
    )
    assert asset.uri is None


def test_derived_asset_requires_concept() -> None:
    with pytest.raises(ValidationError):
        DerivedAsset(
            id="a1",
            kind="immersive_text",
            based_on_concepts=[],
            personalization_profile=_profile(),
        )


def test_derived_asset_rejects_audio_lesson_kind() -> None:
    """Audio lesson is out of scope and must not be a valid kind."""
    with pytest.raises(ValidationError):
        DerivedAsset(
            id="a1",
            kind="audio_lesson",
            based_on_concepts=["c1"],
            personalization_profile=_profile(),
        )


def test_derived_asset_rejects_modality_kinds() -> None:
    """Modality kinds were removed per ADR-0016 and must not validate."""
    for kind in ("slides", "mind_map", "timeline"):
        with pytest.raises(ValidationError):
            DerivedAsset(
                id=f"a-{kind}",
                kind=kind,
                based_on_concepts=["c1"],
                personalization_profile=_profile(),
            )


def test_derived_asset_rejects_phase2_kinds() -> None:
    """Phase-2 assessment kinds were removed per ADR-0016."""
    for kind in ("mnemonic", "image"):
        with pytest.raises(ValidationError):
            DerivedAsset(
                id=f"a-{kind}",
                kind=kind,
                based_on_concepts=["c1"],
                personalization_profile=_profile(),
            )


def test_derived_asset_accepts_immersive_text() -> None:
    asset = DerivedAsset(
        id="a-it",
        kind="immersive_text",
        based_on_concepts=["c1"],
        personalization_profile=_profile(),
    )
    assert asset.kind == "immersive_text"


# ReplacementRecord / PersonalizationProfile --------------------------------


def test_replacement_record_rejects_empty_justification() -> None:
    with pytest.raises(ValidationError):
        ReplacementRecord(
            original_span=_span(),
            replacement_text="new text",
            justification="",
        )


def test_replacement_record_rejects_whitespace_justification() -> None:
    with pytest.raises(ValidationError):
        ReplacementRecord(
            original_span=_span(),
            replacement_text="new text",
            justification="   ",
        )


def test_personalization_profile_round_trip() -> None:
    record = ReplacementRecord(
        original_span=_span(),
        replacement_text="a football analogy",
        justification="Learner listed football as an interest.",
    )
    profile = PersonalizationProfile(
        grade_level="8",
        interests=["football", "coding"],
        replacements=[record],
    )
    rebuilt = PersonalizationProfile.model_validate_json(profile.model_dump_json())
    assert rebuilt == profile


def test_personalization_profile_replacements_default_empty() -> None:
    profile = PersonalizationProfile(grade_level="10", interests=[])
    assert profile.replacements == []


def test_derived_asset_with_typed_profile() -> None:
    profile = PersonalizationProfile(grade_level="6", interests=["space"])
    asset = DerivedAsset(
        id="a1",
        kind="immersive_text",
        based_on_concepts=["c1"],
        personalization_profile=profile,
    )
    assert asset.personalization_profile.grade_level == "6"


# LessonGraph ---------------------------------------------------------------


def test_lesson_graph_round_trip() -> None:
    node = ConceptNode(
        id="c1",
        title="t",
        summary="s",
        learning_objective="lo",
        source_spans=[_span()],
    )
    graph = LessonGraph(id="g1", source_id="s1", concepts=[node])
    payload = graph.model_dump_json()
    rebuilt = LessonGraph.model_validate_json(payload)
    assert rebuilt == graph
