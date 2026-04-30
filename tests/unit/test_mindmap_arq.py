"""Unit tests for the mind_map branch of personalize_concept Arq job.

All external dependencies (db, data_dir, MindMapGenerator) are mocked.
No Ollama, Redis, or filesystem I/O occurs.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lyw_core.db.dao import LESSON_SCOPED_CONCEPT_ID
from lyw_core.validators.base import ValidationError


# ---------------------------------------------------------------------------
# Sentinel constant
# ---------------------------------------------------------------------------


def test_lesson_scoped_concept_id_value() -> None:
    assert LESSON_SCOPED_CONCEPT_ID == "__lesson__"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx() -> dict[str, object]:
    """Return a minimal Arq context with mocked db and data_dir."""
    from lesson_graph import ConceptNode, LessonGraph, SourceSpan

    span = SourceSpan(doc_id="doc-1", page_start=1, page_end=1, char_start=0, char_end=50)
    concept = ConceptNode(
        id="c1",
        title="Root",
        summary="Summary.",
        learning_objective="Understand it.",
        source_spans=[span],
        prerequisites=[],
    )
    graph = LessonGraph(id="lesson-1", source_id="doc-1", concepts=[concept])

    mock_db = AsyncMock()
    mock_db.get_lesson_graph.return_value = graph

    mock_data_dir = MagicMock()
    mock_data_dir.write_asset.return_value = Path("/data/assets/abc.mmd")

    return {
        "db": mock_db,
        "data_dir": mock_data_dir,
        "model_client": MagicMock(),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mind_map_job_writes_asset_and_saves_to_dao() -> None:
    """Happy path: generator returns Mermaid, asset is written and DAO is called."""
    ctx = _make_ctx()
    fake_mermaid = "flowchart TD\n    c1[\"Root\"]\n    c2[\"Branch\"]\n    c1 --> c2\n"

    with patch(
        "lyw_core.worker.jobs.personalize.MindMapGenerator",
        autospec=True,
    ) as MockGenerator:
        instance = MockGenerator.return_value
        instance.generate.return_value = fake_mermaid

        from lyw_core.worker.jobs.personalize import personalize_concept

        result = await personalize_concept(
            ctx,
            lesson_id="lesson-1",
            concept_id=LESSON_SCOPED_CONCEPT_ID,
            profile_id="profile-1",
            kind="mind_map",
        )

    # File was written with .mmd suffix
    ctx["data_dir"].write_asset.assert_called_once()  # type: ignore[union-attr]
    call_kwargs = ctx["data_dir"].write_asset.call_args  # type: ignore[union-attr]
    assert call_kwargs[1].get("suffix") == ".mmd" or (
        len(call_kwargs[0]) >= 2 and call_kwargs[0][1] == ".mmd"
    )
    assert call_kwargs[0][0] == fake_mermaid.encode()

    # DAO save_derived_asset was awaited
    ctx["db"].save_derived_asset.assert_awaited_once()  # type: ignore[union-attr]

    # Saved asset has concept_id = LESSON_SCOPED_CONCEPT_ID
    saved_asset = ctx["db"].save_derived_asset.call_args[0][0]  # type: ignore[union-attr]
    assert saved_asset.concept_id == LESSON_SCOPED_CONCEPT_ID
    assert saved_asset.kind == "mind_map"
    assert saved_asset.lesson_id == "lesson-1"
    assert saved_asset.profile_id == "profile-1"

    # Result dict carries asset_id and file_path
    assert "asset_id" in result
    assert "file_path" in result


@pytest.mark.asyncio
async def test_mind_map_job_uses_lesson_scoped_concept_id_sentinel() -> None:
    """The saved DerivedAsset must use the LESSON_SCOPED_CONCEPT_ID sentinel."""
    ctx = _make_ctx()
    fake_mermaid = "flowchart TD\n    c1[\"Root\"]\n    c2[\"Branch\"]\n    c1 --> c2\n"

    with patch(
        "lyw_core.worker.jobs.personalize.MindMapGenerator",
        autospec=True,
    ) as MockGenerator:
        instance = MockGenerator.return_value
        instance.generate.return_value = fake_mermaid

        from lyw_core.worker.jobs.personalize import personalize_concept

        await personalize_concept(
            ctx,
            lesson_id="lesson-1",
            concept_id=LESSON_SCOPED_CONCEPT_ID,
            profile_id="profile-1",
            kind="mind_map",
        )

    saved_asset = ctx["db"].save_derived_asset.call_args[0][0]  # type: ignore[union-attr]
    assert saved_asset.concept_id == "__lesson__"


@pytest.mark.asyncio
async def test_mind_map_validation_error_propagates() -> None:
    """A ValidationError from run_validators must propagate out of the job."""
    ctx = _make_ctx()

    with (
        patch(
            "lyw_core.worker.jobs.personalize.MindMapGenerator",
            autospec=True,
        ) as MockGenerator,
        patch(
            "lyw_core.worker.jobs.personalize.run_validators",
            side_effect=ValidationError(["mind-map must have at least 2 nodes, found 1"]),
        ),
    ):
        instance = MockGenerator.return_value
        instance.generate.return_value = "flowchart TD\n    c1[\"Only\"]\n"

        from lyw_core.worker.jobs.personalize import personalize_concept

        with pytest.raises(ValidationError, match="at least 2 nodes"):
            await personalize_concept(
                ctx,
                lesson_id="lesson-1",
                concept_id=LESSON_SCOPED_CONCEPT_ID,
                profile_id="profile-1",
                kind="mind_map",
            )

    # DAO must NOT have been called when validation fails
    ctx["db"].save_derived_asset.assert_not_awaited()  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_invalid_kind_raises_value_error() -> None:
    """Passing an unknown kind still raises ValueError immediately."""
    ctx = _make_ctx()

    from lyw_core.worker.jobs.personalize import personalize_concept

    with pytest.raises(ValueError, match="kind must be one of"):
        await personalize_concept(
            ctx,
            lesson_id="lesson-1",
            concept_id="c1",
            profile_id="profile-1",
            kind="unknown_kind",
        )


@pytest.mark.asyncio
async def test_mind_map_lesson_not_found_raises() -> None:
    """Missing lesson raises ValueError before any generation attempt."""
    ctx = _make_ctx()
    ctx["db"].get_lesson_graph.return_value = None  # type: ignore[union-attr]

    with patch(
        "lyw_core.worker.jobs.personalize.MindMapGenerator",
        autospec=True,
    ) as MockGenerator:
        from lyw_core.worker.jobs.personalize import personalize_concept

        with pytest.raises(ValueError, match="lesson not found"):
            await personalize_concept(
                ctx,
                lesson_id="no-such-lesson",
                concept_id=LESSON_SCOPED_CONCEPT_ID,
                profile_id="profile-1",
                kind="mind_map",
            )

        MockGenerator.return_value.generate.assert_not_called()
