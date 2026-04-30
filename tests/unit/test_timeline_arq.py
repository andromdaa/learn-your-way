"""Unit tests for the timeline branch of personalize_concept Arq job.

All external dependencies (db, data_dir, TimelineGenerator) are mocked.
No Ollama, Redis, or filesystem I/O occurs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lyw_core.db.dao import LESSON_SCOPED_CONCEPT_ID
from lyw_core.modalities.timeline import TimelineResult, TimelineSkipped
from lyw_core.validators.base import ValidationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx() -> dict[str, Any]:
    """Return a minimal Arq context with mocked db and data_dir."""
    from lesson_graph import ConceptNode, LessonGraph, SourceSpan
    from lyw_core.profiles.models import LearnerProfile

    span = SourceSpan(
        doc_id="doc-1", page_start=1, page_end=1, char_start=0, char_end=50
    )
    concept = ConceptNode(
        id="c1",
        title="Big Bang",
        summary="The universe began.",
        learning_objective="Understand cosmology.",
        source_spans=[span],
        prerequisites=[],
        temporal_position=1,
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
    mock_data_dir.write_asset.return_value = Path("/data/assets/abc.mmd")

    return {
        "db": mock_db,
        "data_dir": mock_data_dir,
        "model_client": MagicMock(),
    }


def _fake_mermaid() -> str:
    return "timeline\n    section Big Bang\n        The universe began.\n"


# ---------------------------------------------------------------------------
# Non-skip path tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeline_job_writes_asset_and_saves_to_dao() -> None:
    """Happy path: generator returns TimelineResult, asset written, DAO called."""
    ctx = _make_ctx()
    fake_result = TimelineResult(mermaid=_fake_mermaid(), concept_ids=["c1"])

    with patch(
        "lyw_core.worker.jobs.personalize.TimelineGenerator",
        autospec=True,
    ) as mock_generator_cls:
        instance = mock_generator_cls.return_value
        instance.generate.return_value = fake_result

        from lyw_core.worker.jobs.personalize import personalize_concept

        result = await personalize_concept(
            ctx,
            lesson_id="lesson-1",
            concept_id=LESSON_SCOPED_CONCEPT_ID,
            profile_id="profile-1",
            kind="timeline",
        )

    # File was written with .mmd suffix
    ctx["data_dir"].write_asset.assert_called_once()
    call_args = ctx["data_dir"].write_asset.call_args
    assert call_args[1].get("suffix") == ".mmd" or (
        len(call_args[0]) >= 2 and call_args[0][1] == ".mmd"
    )
    assert call_args[0][0] == _fake_mermaid().encode()

    # DAO save_derived_asset was awaited
    ctx["db"].save_derived_asset.assert_awaited_once()

    # Saved asset has concept_id = LESSON_SCOPED_CONCEPT_ID
    saved_asset = ctx["db"].save_derived_asset.call_args[0][0]
    assert saved_asset.concept_id == LESSON_SCOPED_CONCEPT_ID
    assert saved_asset.kind == "timeline"
    assert saved_asset.lesson_id == "lesson-1"
    assert saved_asset.profile_id == "profile-1"

    # Result dict carries asset_id and file_path
    assert "asset_id" in result
    assert "file_path" in result


@pytest.mark.asyncio
async def test_timeline_job_uses_lesson_scoped_concept_id_sentinel() -> None:
    """The saved DerivedAsset must use the LESSON_SCOPED_CONCEPT_ID sentinel."""
    ctx = _make_ctx()
    fake_result = TimelineResult(mermaid=_fake_mermaid(), concept_ids=["c1"])

    with patch(
        "lyw_core.worker.jobs.personalize.TimelineGenerator",
        autospec=True,
    ) as mock_generator_cls:
        instance = mock_generator_cls.return_value
        instance.generate.return_value = fake_result

        from lyw_core.worker.jobs.personalize import personalize_concept

        await personalize_concept(
            ctx,
            lesson_id="lesson-1",
            concept_id=LESSON_SCOPED_CONCEPT_ID,
            profile_id="profile-1",
            kind="timeline",
        )

    saved_asset = ctx["db"].save_derived_asset.call_args[0][0]
    assert saved_asset.concept_id == "__lesson__"


# ---------------------------------------------------------------------------
# Skip path tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeline_skip_path_returns_skipped_payload() -> None:
    """When generator returns TimelineSkipped, job returns skipped payload."""
    ctx = _make_ctx()

    with patch(
        "lyw_core.worker.jobs.personalize.TimelineGenerator",
        autospec=True,
    ) as mock_generator_cls:
        instance = mock_generator_cls.return_value
        instance.generate.return_value = TimelineSkipped()

        from lyw_core.worker.jobs.personalize import personalize_concept

        result = await personalize_concept(
            ctx,
            lesson_id="lesson-1",
            concept_id=LESSON_SCOPED_CONCEPT_ID,
            profile_id="profile-1",
            kind="timeline",
        )

    assert result.get("skipped") is True
    assert result.get("reason") == "no_temporal_metadata"


@pytest.mark.asyncio
async def test_timeline_skip_path_does_not_write_asset() -> None:
    """Skip path must not write any file to data_dir."""
    ctx = _make_ctx()

    with patch(
        "lyw_core.worker.jobs.personalize.TimelineGenerator",
        autospec=True,
    ) as mock_generator_cls:
        instance = mock_generator_cls.return_value
        instance.generate.return_value = TimelineSkipped()

        from lyw_core.worker.jobs.personalize import personalize_concept

        await personalize_concept(
            ctx,
            lesson_id="lesson-1",
            concept_id=LESSON_SCOPED_CONCEPT_ID,
            profile_id="profile-1",
            kind="timeline",
        )

    ctx["data_dir"].write_asset.assert_not_called()


@pytest.mark.asyncio
async def test_timeline_skip_path_does_not_call_dao() -> None:
    """Skip path must not persist anything to the DAO."""
    ctx = _make_ctx()

    with patch(
        "lyw_core.worker.jobs.personalize.TimelineGenerator",
        autospec=True,
    ) as mock_generator_cls:
        instance = mock_generator_cls.return_value
        instance.generate.return_value = TimelineSkipped()

        from lyw_core.worker.jobs.personalize import personalize_concept

        await personalize_concept(
            ctx,
            lesson_id="lesson-1",
            concept_id=LESSON_SCOPED_CONCEPT_ID,
            profile_id="profile-1",
            kind="timeline",
        )

    ctx["db"].save_derived_asset.assert_not_awaited()


# ---------------------------------------------------------------------------
# Validation error path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeline_validation_error_propagates() -> None:
    """A ValidationError from run_validators must propagate out of the job."""
    ctx = _make_ctx()
    fake_result = TimelineResult(mermaid="bad output", concept_ids=["c1"])

    with (
        patch(
            "lyw_core.worker.jobs.personalize.TimelineGenerator",
            autospec=True,
        ) as mock_generator_cls,
        patch(
            "lyw_core.worker.jobs.personalize.run_validators",
            side_effect=ValidationError(["timeline must have at least one section"]),
        ),
    ):
        instance = mock_generator_cls.return_value
        instance.generate.return_value = fake_result

        from lyw_core.worker.jobs.personalize import personalize_concept

        with pytest.raises(ValidationError, match="at least one section"):
            await personalize_concept(
                ctx,
                lesson_id="lesson-1",
                concept_id=LESSON_SCOPED_CONCEPT_ID,
                profile_id="profile-1",
                kind="timeline",
            )

    # DAO must NOT have been called when validation fails
    ctx["db"].save_derived_asset.assert_not_awaited()
