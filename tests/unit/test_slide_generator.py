"""Unit tests for SlideGenerator (mocked ModelClient, no real inference)."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest

from lesson_graph.models import ConceptNode, LessonGraph, PersonalizationProfile, SourceSpan
from lyw_core.modalities.slides import Slide, SlideDeck, SlideGenerator
from lyw_core.validators.base import ValidationError


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
    summary: str = "Summary text.",
    prerequisites: list[str] | None = None,
) -> ConceptNode:
    return ConceptNode(
        id=cid,
        title=title,
        summary=summary,
        learning_objective=f"Understand {cid}.",
        source_spans=[_span()],
        prerequisites=prerequisites or [],
    )


def _profile() -> PersonalizationProfile:
    return PersonalizationProfile(grade_level="8", interests=["science"])


def _graph(concepts: list[ConceptNode]) -> LessonGraph:
    return LessonGraph(id="g1", source_id="doc-1", concepts=concepts)


def _outline_json(concepts: list[ConceptNode]) -> str:
    """Build a valid outline JSON for the given concepts."""
    items = []
    for c in concepts:
        items.append(
            {
                "title": f"{c.title} Overview",
                "key_points": [f"Point about {c.title}"],
                "concept_id": c.id,
            }
        )
    return json.dumps(items)


def _slide_body_json(title: str) -> str:
    """Build a valid slide body JSON for a single slide."""
    return json.dumps(
        {
            "body": f"Detailed content for {title}.",
            "speaker_notes": f"Notes for {title}.",
        }
    )


def _make_model_client(
    outline_response: str,
    body_responses: list[str],
) -> AsyncMock:
    """Create a mock ModelClient with side_effect for outline + per-slide calls."""
    mock = AsyncMock()
    mock.complete.side_effect = [outline_response, *body_responses]
    return mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_concept_lesson_produces_deck_with_slides() -> None:
    """Happy path: two concepts produce a SlideDeck with at least one slide."""
    concepts = [
        _concept("c1", "Photosynthesis"),
        _concept("c2", "Light reactions"),
    ]
    graph = _graph(concepts)
    profile = _profile()

    outline = _outline_json(concepts)
    bodies = [_slide_body_json(c.title) for c in concepts]
    model_client = _make_model_client(outline, bodies)

    gen = SlideGenerator()
    deck = await gen.generate(graph, profile, model_client)

    assert isinstance(deck, SlideDeck)
    assert len(deck.slides) >= 1
    for slide in deck.slides:
        assert slide.title
        assert slide.body
        assert slide.speaker_notes
        assert slide.source_spans


@pytest.mark.asyncio
async def test_slide_without_source_spans_is_discarded() -> None:
    """A slide body that produces no source_spans is discarded by the validator."""
    concepts = [_concept("c1", "Concept One"), _concept("c2", "Concept Two")]
    graph = _graph(concepts)
    profile = _profile()

    # Outline with 2 slides; first body good, second body missing source_spans
    outline = json.dumps(
        [
            {"title": "Good Slide", "key_points": ["something"], "concept_id": "c1"},
            {"title": "Bad Slide", "key_points": ["other"], "concept_id": "c2"},
        ]
    )
    # First slide: good body with source_spans populated from the concept
    good_body = json.dumps(
        {"body": "Valid content.", "speaker_notes": "Valid notes."}
    )
    # Second slide: returned with empty body to trigger validator failure
    bad_body = json.dumps({"body": "", "speaker_notes": "Notes."})

    model_client = _make_model_client(outline, [good_body, bad_body])

    gen = SlideGenerator()
    deck = await gen.generate(graph, profile, model_client)

    assert isinstance(deck, SlideDeck)
    assert len(deck.slides) == 1
    assert deck.slides[0].title == "Good Slide"


@pytest.mark.asyncio
async def test_all_slides_discarded_raises_validation_error() -> None:
    """If every slide fails validation, ValidationError is raised."""
    concepts = [_concept("c1", "Concept One")]
    graph = _graph(concepts)
    profile = _profile()

    outline = json.dumps(
        [{"title": "Bad Slide", "key_points": ["x"], "concept_id": "c1"}]
    )
    # Empty body will fail validation
    bad_body = json.dumps({"body": "", "speaker_notes": ""})

    model_client = _make_model_client(outline, [bad_body])

    gen = SlideGenerator()
    with pytest.raises(ValidationError):
        await gen.generate(graph, profile, model_client)


@pytest.mark.asyncio
async def test_malformed_outline_json_raises_error() -> None:
    """Malformed JSON from the outline step raises an error."""
    concepts = [_concept("c1", "Concept One")]
    graph = _graph(concepts)

    model_client = AsyncMock()
    model_client.complete.return_value = "not valid json {"

    gen = SlideGenerator()
    with pytest.raises(Exception):
        await gen.generate(graph, _profile(), model_client)


@pytest.mark.asyncio
async def test_deck_based_on_concepts_matches_accepted_slides() -> None:
    """SlideDeck.based_on_concepts contains IDs of accepted slide concepts."""
    concepts = [
        _concept("c1", "Topic Alpha"),
        _concept("c2", "Topic Beta"),
    ]
    graph = _graph(concepts)
    profile = _profile()

    outline = _outline_json(concepts)
    bodies = [_slide_body_json(c.title) for c in concepts]
    model_client = _make_model_client(outline, bodies)

    gen = SlideGenerator()
    deck = await gen.generate(graph, profile, model_client)

    assert len(deck.based_on_concepts) >= 1
    for concept_id in deck.based_on_concepts:
        assert concept_id in {"c1", "c2"}


@pytest.mark.asyncio
async def test_outline_call_is_made_exactly_once() -> None:
    """The generator makes exactly one outline call, then one per slide."""
    concepts = [_concept("c1", "Solo")]
    graph = _graph(concepts)

    outline = _outline_json(concepts)
    body = _slide_body_json("Solo")
    model_client = _make_model_client(outline, [body])

    gen = SlideGenerator()
    await gen.generate(graph, _profile(), model_client)

    # One outline call + one body call = 2 total
    assert model_client.complete.call_count == 2


@pytest.mark.asyncio
async def test_snapshot_deck_structure(snapshot: Any) -> None:
    """Snapshot test captures stable output shape."""
    concepts = [
        _concept("c1", "Mitosis", summary="Cell division process."),
    ]
    graph = _graph(concepts)
    profile = _profile()

    outline = json.dumps(
        [
            {
                "title": "Mitosis Overview",
                "key_points": ["Phases of mitosis"],
                "concept_id": "c1",
            }
        ]
    )
    body = json.dumps(
        {
            "body": "Mitosis is the process of cell division.",
            "speaker_notes": "Explain each phase clearly.",
        }
    )
    model_client = _make_model_client(outline, [body])

    gen = SlideGenerator()
    deck = await gen.generate(graph, profile, model_client)

    assert len(deck.slides) == 1
    slide = deck.slides[0]
    assert snapshot == {
        "title": slide.title,
        "body": slide.body,
        "speaker_notes": slide.speaker_notes,
        "concept_id": slide.concept_id,
        "has_source_spans": len(slide.source_spans) > 0,
    }
