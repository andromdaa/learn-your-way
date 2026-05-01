"""Arq personalize_concept job: generate and persist a derived asset."""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from lyw_core.clients.ollama import OllamaError
from lyw_core.db.dao import Database, DerivedAsset
from lyw_core.personalization.relevel import ReLeveler
from lyw_core.personalization.replace import ExampleReplacer, ReplaceSourceTooThinError
from lyw_core.storage.fs import DataDir
from lyw_core.validators.base import ValidationError
from lyw_core.validators.faithfulness import SourceFaithfulnessValidator
from lyw_core.worker.jobs._progress import make_progress
from lyw_core.worker.result import Failure, Success

_logger = structlog.get_logger(__name__)

_VALID_KINDS = frozenset({"relevel", "replace"})


async def personalize_concept(
    ctx: dict[str, Any],
    *,
    lesson_id: str,
    concept_id: str,
    profile_id: str,
    kind: str,
) -> Success[dict[str, Any]] | Failure:
    """Generate and persist a derived asset.

    Returns a Success with ``asset_id`` and ``file_path`` on the happy path,
    or a Failure with a typed ``code`` for every domain error. No exception
    is raised across the Arq pickle boundary.
    """
    if kind not in _VALID_KINDS:
        return Failure(
            code="invalid_kind",
            message=f"kind must be one of {sorted(_VALID_KINDS)!r}, got {kind!r}",
        )

    progress = make_progress(ctx, lesson_id=lesson_id)
    await progress.emit(phase="kind_resolved", pct=0.0, data={"kind": kind})

    db: Database = ctx["db"]
    data_dir: DataDir = ctx["data_dir"]
    model_client = ctx["model_client"]

    lesson_graph = await db.get_lesson_graph(lesson_id)
    if lesson_graph is None:
        return Failure(
            code="lesson_not_found",
            message=f"lesson not found: {lesson_id!r}",
        )

    concept = next(
        (c for c in lesson_graph.concepts if c.id == concept_id),
        None,
    )
    if concept is None:
        return Failure(
            code="concept_not_found",
            message=f"concept {concept_id!r} not found in lesson {lesson_id!r}",
        )

    profile = await db.get_profile(profile_id)
    if profile is None:
        return Failure(
            code="profile_not_found",
            message=f"profile not found: {profile_id!r}",
        )

    faithfulness = SourceFaithfulnessValidator()

    try:
        if kind == "relevel":
            gen_relevel = ReLeveler(
                model_client=model_client,
                faithfulness_validator=faithfulness,
            )
            content, _ = await gen_relevel.relevel(concept, profile, lesson_graph)
        else:  # replace
            gen_replace = ExampleReplacer(
                model_client=model_client,
                faithfulness_validator=faithfulness,
            )
            records = await gen_replace.replace(concept, profile, lesson_graph)
            content = "\n\n".join(r.replacement_text for r in records)
    except ReplaceSourceTooThinError as exc:
        await progress.fail(
            str(exc),
            details={
                "concept_id": exc.concept_id,
                "char_count": exc.char_count,
                "word_count": exc.word_count,
            },
        )
        return Failure(
            code="thin_source",
            message=str(exc),
            details={
                "concept_id": exc.concept_id,
                "char_count": exc.char_count,
                "word_count": exc.word_count,
            },
        )
    except OllamaError as exc:
        await progress.fail(str(exc), details={"status_code": exc.status_code})
        return Failure(
            code="ollama_error",
            message=str(exc),
            details={"status_code": exc.status_code},
        )
    except ValidationError as exc:
        await progress.fail(str(exc), details={"reasons": exc.reasons})
        return Failure(
            code="validation_failed",
            message=str(exc),
            details={"reasons": exc.reasons},
        )

    file_path = data_dir.write_asset(content.encode(), suffix=".txt")

    asset_id = str(uuid.uuid4())
    asset = DerivedAsset(
        id=asset_id,
        lesson_id=lesson_id,
        concept_id=concept_id,
        kind=kind,
        profile_id=profile_id,
        file_path=str(file_path),
        created_at="",  # filled by SQLite DEFAULT
    )
    await db.save_derived_asset(asset)

    _logger.info(
        "derived_asset_persisted",
        asset_id=asset_id,
        lesson_id=lesson_id,
        concept_id=concept_id,
        kind=kind,
        profile_id=profile_id,
        file_path=str(file_path),
    )
    raw_result = {"asset_id": asset_id, "file_path": str(file_path)}
    await progress.done(raw_result)
    return Success(payload=raw_result)
