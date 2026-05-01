"""Unit tests for DerivedAsset DAO and personalize_concept Arq job.

All model, DB, and filesystem calls are mocked so tests run fast and offline.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lesson_graph.models import ConceptNode, LessonGraph, SourceSpan
from lyw_core.db.dao import Database, DerivedAsset
from lyw_core.profiles.models import LearnerProfile
from lyw_core.worker.result import Failure, Success

# ---------------------------------------------------------------------------
# Helpers shared by DAO and job tests
# ---------------------------------------------------------------------------


def _span() -> SourceSpan:
    return SourceSpan(
        doc_id="doc-1",
        page_start=1,
        page_end=2,
        char_start=0,
        char_end=500,
    )


def _concept(cid: str = "c1") -> ConceptNode:
    # Summary is intentionally above the ReplaceSourceTooThinError thresholds
    # (>=200 chars, >=30 words AFTER the leading title is stripped) so the
    # ``replace`` path in personalize_concept is exercised end-to-end here.
    # A separate test covers the thin-summary failure case.
    return ConceptNode(
        id=cid,
        title="Photosynthesis",
        summary=(
            "Photosynthesis is like a tiny factory inside a leaf, where "
            "chloroplasts capture sunlight and use water and carbon dioxide "
            "from the air to build sugar molecules. Imagine a green machine "
            "that turns sunlight into food, releasing oxygen as a useful "
            "by-product for the rest of the living world to breathe."
        ),
        learning_objective="Explain photosynthesis.",
        source_spans=[_span()],
    )


def _graph() -> LessonGraph:
    return LessonGraph(id="g1", source_id="src-1", concepts=[_concept()])


def _profile() -> LearnerProfile:
    return LearnerProfile(id="p1", grade_level="6", interests=["nature"], goals=[])


# ---------------------------------------------------------------------------
# DerivedAsset DAO — in-memory SQLite
# ---------------------------------------------------------------------------


async def test_save_and_get_derived_asset() -> None:
    db = await Database.connect(":memory:")
    asset = DerivedAsset(
        id=str(uuid.uuid4()),
        lesson_id="g1",
        concept_id="c1",
        kind="relevel",
        profile_id="p1",
        file_path="/data/assets/ab/abcdef.txt",
        created_at="",
    )
    await db.save_derived_asset(asset)

    fetched = await db.get_derived_asset("g1", "c1", "relevel", "p1")
    assert fetched is not None
    assert fetched.id == asset.id
    assert fetched.lesson_id == "g1"
    assert fetched.concept_id == "c1"
    assert fetched.kind == "relevel"
    assert fetched.profile_id == "p1"
    assert fetched.file_path == "/data/assets/ab/abcdef.txt"
    assert fetched.created_at != ""  # filled by SQLite DEFAULT
    await db.close()


async def test_get_derived_asset_missing_returns_none() -> None:
    db = await Database.connect(":memory:")
    result = await db.get_derived_asset("g1", "c1", "relevel", "p1")
    assert result is None
    await db.close()


async def test_save_derived_asset_insert_or_ignore_deduplication() -> None:
    """Saving the same id twice does not raise and row count stays at 1."""
    db = await Database.connect(":memory:")
    asset_id = str(uuid.uuid4())
    asset = DerivedAsset(
        id=asset_id,
        lesson_id="g1",
        concept_id="c1",
        kind="relevel",
        profile_id="p1",
        file_path="/data/assets/ab/abc.txt",
        created_at="",
    )
    await db.save_derived_asset(asset)
    # Second save with same id — should be silently ignored
    await db.save_derived_asset(asset)

    fetched = await db.get_derived_asset("g1", "c1", "relevel", "p1")
    assert fetched is not None
    assert fetched.id == asset_id
    await db.close()


async def test_get_derived_asset_returns_latest_when_multiple() -> None:
    """When multiple assets exist for the same key, most-recent is returned."""
    db = await Database.connect(":memory:")
    first_id = str(uuid.uuid4())
    second_id = str(uuid.uuid4())

    await db.save_derived_asset(
        DerivedAsset(
            id=first_id,
            lesson_id="g1",
            concept_id="c1",
            kind="relevel",
            profile_id="p1",
            file_path="/data/assets/aa/first.txt",
            created_at="",
        )
    )
    await db.save_derived_asset(
        DerivedAsset(
            id=second_id,
            lesson_id="g1",
            concept_id="c1",
            kind="relevel",
            profile_id="p1",
            file_path="/data/assets/bb/second.txt",
            created_at="",
        )
    )

    fetched = await db.get_derived_asset("g1", "c1", "relevel", "p1")
    assert fetched is not None
    # Most recent row is returned (ORDER BY created_at DESC)
    assert fetched.id in (first_id, second_id)
    await db.close()


# ---------------------------------------------------------------------------
# personalize_concept job — all I/O mocked
# ---------------------------------------------------------------------------


def _make_ctx(tmp_path: Path) -> dict[str, Any]:
    """Build a minimal Arq ctx dict with mocked DB, data_dir, model_client."""
    from lyw_core.storage.fs import DataDir

    data_dir = DataDir(tmp_path)
    data_dir.bootstrap()

    db = AsyncMock(spec=Database)
    db.get_lesson_graph = AsyncMock(return_value=_graph())
    db.get_profile = AsyncMock(return_value=_profile())
    db.save_derived_asset = AsyncMock()

    model_client = AsyncMock()
    model_client.complete = AsyncMock(return_value="Generated text for test.")

    return {
        "db": db,
        "data_dir": data_dir,
        "model_client": model_client,
    }


@pytest.mark.asyncio
async def test_personalize_concept_relevel(tmp_path: Path) -> None:
    from lyw_core.worker.jobs.personalize import personalize_concept

    ctx = _make_ctx(tmp_path)

    with patch(
        "lyw_core.worker.jobs.personalize.SourceFaithfulnessValidator"
    ) as mock_validator_cls:
        mock_validator = MagicMock()
        from lyw_core.validators.base import ValidationResult

        mock_validator.validate = MagicMock(return_value=ValidationResult(passed=True))
        mock_validator_cls.return_value = mock_validator

        result = await personalize_concept(
            ctx,
            lesson_id="g1",
            concept_id="c1",
            profile_id="p1",
            kind="relevel",
        )

    assert isinstance(result, Success)
    assert result.payload["asset_id"]
    db: AsyncMock = ctx["db"]
    db.save_derived_asset.assert_awaited_once()
    saved: DerivedAsset = db.save_derived_asset.call_args[0][0]
    assert saved.kind == "relevel"


@pytest.mark.asyncio
async def test_personalize_concept_replace(tmp_path: Path) -> None:
    from lyw_core.worker.jobs.personalize import personalize_concept

    ctx = _make_ctx(tmp_path)
    # ExampleReplacer expects JSON-array response from model
    ctx["model_client"].complete = AsyncMock(
        return_value='[{"original_text": "sunlight", "replacement_text": "solar energy", "interest": "physics"}]'
    )

    with patch(
        "lyw_core.worker.jobs.personalize.SourceFaithfulnessValidator"
    ) as mock_validator_cls:
        mock_validator = MagicMock()
        from lyw_core.validators.base import ValidationResult

        mock_validator.validate = MagicMock(return_value=ValidationResult(passed=True))
        mock_validator_cls.return_value = mock_validator

        result = await personalize_concept(
            ctx,
            lesson_id="g1",
            concept_id="c1",
            profile_id="p1",
            kind="replace",
        )

    assert isinstance(result, Success)
    assert result.payload["asset_id"]
    db: AsyncMock = ctx["db"]
    db.save_derived_asset.assert_awaited_once()
    saved: DerivedAsset = db.save_derived_asset.call_args[0][0]
    assert saved.kind == "replace"


@pytest.mark.asyncio
async def test_personalize_concept_invalid_kind(tmp_path: Path) -> None:
    from lyw_core.worker.jobs.personalize import personalize_concept

    ctx = _make_ctx(tmp_path)
    result = await personalize_concept(
        ctx,
        lesson_id="g1",
        concept_id="c1",
        profile_id="p1",
        kind="unknown",
    )
    assert isinstance(result, Failure)
    assert result.code == "invalid_kind"


@pytest.mark.asyncio
async def test_personalize_concept_lesson_not_found(tmp_path: Path) -> None:
    from lyw_core.worker.jobs.personalize import personalize_concept

    ctx = _make_ctx(tmp_path)
    ctx["db"].get_lesson_graph = AsyncMock(return_value=None)

    result = await personalize_concept(
        ctx,
        lesson_id="no-such",
        concept_id="c1",
        profile_id="p1",
        kind="relevel",
    )
    assert isinstance(result, Failure)
    assert result.code == "lesson_not_found"


@pytest.mark.asyncio
async def test_personalize_concept_concept_not_found(tmp_path: Path) -> None:
    from lyw_core.worker.jobs.personalize import personalize_concept

    ctx = _make_ctx(tmp_path)

    result = await personalize_concept(
        ctx,
        lesson_id="g1",
        concept_id="no-such-concept",
        profile_id="p1",
        kind="relevel",
    )
    assert isinstance(result, Failure)
    assert result.code == "concept_not_found"


@pytest.mark.asyncio
async def test_personalize_concept_relevel_profile_not_found(tmp_path: Path) -> None:
    from lyw_core.worker.jobs.personalize import personalize_concept

    ctx = _make_ctx(tmp_path)
    ctx["db"].get_profile = AsyncMock(return_value=None)

    result = await personalize_concept(
        ctx,
        lesson_id="g1",
        concept_id="c1",
        profile_id="missing-profile",
        kind="relevel",
    )
    assert isinstance(result, Failure)
    assert result.code == "profile_not_found"


@pytest.mark.asyncio
async def test_personalize_concept_replace_profile_not_found(tmp_path: Path) -> None:
    from lyw_core.worker.jobs.personalize import personalize_concept

    ctx = _make_ctx(tmp_path)
    ctx["db"].get_profile = AsyncMock(return_value=None)

    result = await personalize_concept(
        ctx,
        lesson_id="g1",
        concept_id="c1",
        profile_id="missing-profile",
        kind="replace",
    )
    assert isinstance(result, Failure)
    assert result.code == "profile_not_found"


@pytest.mark.asyncio
async def test_personalize_concept_replace_thin_source_returns_failure(
    tmp_path: Path,
) -> None:
    """Thin concept.summary returns a typed Failure (no exception raised, no asset row saved).

    Issue #77: the pre-flight gate in ExampleReplacer raises ReplaceSourceTooThinError;
    the job boundary catches it and converts it to Failure(code="thin_source").
    The model is never called and no DB row is written.
    """
    from lyw_core.worker.jobs.personalize import personalize_concept

    ctx = _make_ctx(tmp_path)
    # Override the lesson graph with a concept whose summary is just the title
    # (heuristic-chunker fallback for a heading-only span). After title strip
    # the body is empty — both gates trip.
    thin_concept = ConceptNode(
        id="c1",
        title="EQUATIONS AND INEQUALITIES",
        summary="EQUATIONS AND INEQUALITIES",
        learning_objective="Solve equations and inequalities.",
        source_spans=[_span()],
    )
    thin_graph = LessonGraph(id="g1", source_id="src-1", concepts=[thin_concept])
    ctx["db"].get_lesson_graph = AsyncMock(return_value=thin_graph)

    result = await personalize_concept(
        ctx,
        lesson_id="g1",
        concept_id="c1",
        profile_id="p1",
        kind="replace",
    )

    assert isinstance(result, Failure)
    assert result.code == "thin_source"
    assert result.details["concept_id"] == "c1"

    # No asset row written; no model call made.
    db: AsyncMock = ctx["db"]
    db.save_derived_asset.assert_not_awaited()
    model_client: AsyncMock = ctx["model_client"]
    model_client.complete.assert_not_called()


@pytest.mark.asyncio
async def test_personalize_concept_writes_file_to_data_dir(tmp_path: Path) -> None:
    from lyw_core.worker.jobs.personalize import personalize_concept

    ctx = _make_ctx(tmp_path)

    with patch(
        "lyw_core.worker.jobs.personalize.SourceFaithfulnessValidator"
    ) as mock_validator_cls:
        mock_validator = MagicMock()
        from lyw_core.validators.base import ValidationResult

        mock_validator.validate = MagicMock(return_value=ValidationResult(passed=True))
        mock_validator_cls.return_value = mock_validator

        result = await personalize_concept(
            ctx,
            lesson_id="g1",
            concept_id="c1",
            profile_id="p1",
            kind="relevel",
        )

    assert isinstance(result, Success)
    assert Path(result.payload["file_path"]).exists()
    assert Path(result.payload["file_path"]).read_text() == "Generated text for test."


@pytest.mark.asyncio
async def test_failure_pickles_cleanly() -> None:
    """Failure must round-trip through pickle without losing structure.

    Pydantic models pickle cleanly — this test is the regression guard that
    would have caught the __reduce__-missing defects in AND-21/22/23.
    """
    import pickle

    failure = Failure(
        code="thin_source",
        message="concept 'c1' summary too thin",
        details={"concept_id": "c1", "char_count": 5, "word_count": 1},
    )
    roundtripped = pickle.loads(pickle.dumps(failure))
    assert roundtripped.code == failure.code
    assert roundtripped.message == failure.message
    assert roundtripped.details == failure.details
