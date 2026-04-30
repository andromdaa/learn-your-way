"""Unit tests for the slides branch of personalize_concept Arq job.

All external dependencies (db, data_dir, SlideGenerator) are mocked.
No Ollama, Redis, or filesystem I/O occurs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lesson_graph import ConceptNode, LessonGraph, SourceSpan
from lyw_core.db.dao import LESSON_SCOPED_CONCEPT_ID
from lyw_core.modalities.slides import Slide, SlideDeck
from lyw_core.profiles.models import LearnerProfile
from lyw_core.validators.base import ValidationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx() -> dict[str, Any]:
    """Return a minimal Arq context with mocked db and data_dir."""
    span = SourceSpan(
        doc_id="doc-1", page_start=1, page_end=1, char_start=0, char_end=50
    )
    concept = ConceptNode(
        id="c1",
        title="Photosynthesis",
        summary="How plants make food.",
        learning_objective="Understand photosynthesis.",
        source_spans=[span],
        prerequisites=[],
    )
    graph = LessonGraph(id="lesson-1", source_id="doc-1", concepts=[concept])
    learner_profile = LearnerProfile(
        id="profile-1",
        grade_level="8",
        interests=["science"],
        goals=["understand basics"],
    )

    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = graph
    mock_db.get_profile.return_value = learner_profile

    mock_data_dir = MagicMock()
    mock_data_dir.write_asset.return_value = Path("/data/assets/abc.json")

    return {
        "db": mock_db,
        "data_dir": mock_data_dir,
        "model_client": MagicMock(),
    }


def _fake_deck() -> SlideDeck:
    """Return a minimal two-slide SlideDeck for testing."""
    span = SourceSpan(
        doc_id="doc-1", page_start=1, page_end=1, char_start=0, char_end=50
    )
    slides = [
        Slide(
            title="Slide One",
            body="Body content one.",
            speaker_notes="Notes for one.",
            source_spans=[span],
            concept_id="c1",
        ),
        Slide(
            title="Slide Two",
            body="Body content two.",
            speaker_notes="Notes for two.",
            source_spans=[span],
            concept_id="c1",
        ),
    ]
    return SlideDeck(slides=slides, based_on_concepts=["c1"])


# ---------------------------------------------------------------------------
# Tests: slides branch happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_slides_job_writes_json_asset_and_saves_to_dao() -> None:
    """Happy path: generator returns SlideDeck, JSON written, DAO persisted."""
    ctx = _make_ctx()
    deck = _fake_deck()

    with patch(
        "lyw_core.worker.jobs.personalize.SlideGenerator",
        autospec=True,
    ) as mock_generator_cls:
        instance = mock_generator_cls.return_value
        instance.generate = AsyncMock(return_value=deck)

        from lyw_core.worker.jobs.personalize import personalize_concept

        result = await personalize_concept(
            ctx,
            lesson_id="lesson-1",
            concept_id=LESSON_SCOPED_CONCEPT_ID,
            profile_id="profile-1",
            kind="slides",
        )

    # File was written with .json suffix
    ctx["data_dir"].write_asset.assert_called_once()
    call_args = ctx["data_dir"].write_asset.call_args
    assert call_args[1].get("suffix") == ".json" or (
        len(call_args[0]) >= 2 and call_args[0][1] == ".json"
    )

    # Written bytes are valid JSON
    written_bytes = call_args[0][0]
    deck_data = json.loads(written_bytes.decode())
    assert "slides" in deck_data
    assert len(deck_data["slides"]) == 2

    # DAO save_derived_asset was awaited
    ctx["db"].save_derived_asset.assert_awaited_once()

    # Saved asset has concept_id = LESSON_SCOPED_CONCEPT_ID and kind = "slides"
    saved_asset = ctx["db"].save_derived_asset.call_args[0][0]
    assert saved_asset.concept_id == LESSON_SCOPED_CONCEPT_ID
    assert saved_asset.kind == "slides"
    assert saved_asset.lesson_id == "lesson-1"
    assert saved_asset.profile_id == "profile-1"

    # Result dict carries asset_id and file_path
    assert "asset_id" in result
    assert "file_path" in result


@pytest.mark.asyncio
async def test_slides_job_uses_lesson_scoped_concept_id_sentinel() -> None:
    """The saved DerivedAsset must use the LESSON_SCOPED_CONCEPT_ID sentinel."""
    ctx = _make_ctx()

    with patch(
        "lyw_core.worker.jobs.personalize.SlideGenerator",
        autospec=True,
    ) as mock_generator_cls:
        instance = mock_generator_cls.return_value
        instance.generate = AsyncMock(return_value=_fake_deck())

        from lyw_core.worker.jobs.personalize import personalize_concept

        await personalize_concept(
            ctx,
            lesson_id="lesson-1",
            concept_id=LESSON_SCOPED_CONCEPT_ID,
            profile_id="profile-1",
            kind="slides",
        )

    saved_asset = ctx["db"].save_derived_asset.call_args[0][0]
    assert saved_asset.concept_id == "__lesson__"


@pytest.mark.asyncio
async def test_slides_json_serialises_deck_structure() -> None:
    """SlideDeck is serialised to valid JSON with expected structure."""
    ctx = _make_ctx()
    deck = _fake_deck()

    with patch(
        "lyw_core.worker.jobs.personalize.SlideGenerator",
        autospec=True,
    ) as mock_generator_cls:
        instance = mock_generator_cls.return_value
        instance.generate = AsyncMock(return_value=deck)

        from lyw_core.worker.jobs.personalize import personalize_concept

        await personalize_concept(
            ctx,
            lesson_id="lesson-1",
            concept_id=LESSON_SCOPED_CONCEPT_ID,
            profile_id="profile-1",
            kind="slides",
        )

    written_bytes = ctx["data_dir"].write_asset.call_args[0][0]
    deck_data = json.loads(written_bytes.decode())
    # SlideDeck dataclass has 'slides' and 'based_on_concepts' fields
    assert "slides" in deck_data
    assert "based_on_concepts" in deck_data
    assert len(deck_data["slides"]) == 2
    # Each slide has the expected fields
    slide_data = deck_data["slides"][0]
    assert "title" in slide_data
    assert "body" in slide_data
    assert "speaker_notes" in slide_data
    assert "source_spans" in slide_data
    assert "concept_id" in slide_data


# ---------------------------------------------------------------------------
# Tests: validation error propagation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_slides_validation_error_propagates() -> None:
    """ValidationError from SlideGenerator must propagate; DAO not called."""
    ctx = _make_ctx()

    with patch(
        "lyw_core.worker.jobs.personalize.SlideGenerator",
        autospec=True,
    ) as mock_generator_cls:
        instance = mock_generator_cls.return_value
        instance.generate = AsyncMock(
            side_effect=ValidationError(["all slides were discarded"])
        )

        from lyw_core.worker.jobs.personalize import personalize_concept

        with pytest.raises(ValidationError, match="all slides were discarded"):
            await personalize_concept(
                ctx,
                lesson_id="lesson-1",
                concept_id=LESSON_SCOPED_CONCEPT_ID,
                profile_id="profile-1",
                kind="slides",
            )

    ctx["db"].save_derived_asset.assert_not_awaited()
