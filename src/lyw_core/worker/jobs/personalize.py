"""Arq personalize_concept job: generate and persist a derived asset."""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from lyw_core.assessment.mnemonic import MnemonicGenerator
from lyw_core.db.dao import Database, DerivedAsset
from lyw_core.personalization.relevel import ReLeveler
from lyw_core.personalization.replace import ExampleReplacer
from lyw_core.storage.fs import DataDir
from lyw_core.validators.faithfulness import SourceFaithfulnessValidator
from lyw_core.worker.jobs._progress import make_progress

_logger = structlog.get_logger(__name__)

_VALID_KINDS = frozenset({"relevel", "replace", "mnemonic"})


async def personalize_concept(
    ctx: dict[str, Any],
    *,
    lesson_id: str,
    concept_id: str,
    profile_id: str,
    kind: str,
) -> dict[str, Any]:
    """Generate and persist a derived asset.

    Returns
    -------
    dict with ``asset_id`` and ``file_path`` keys.
    """
    if kind not in _VALID_KINDS:
        raise ValueError(f"kind must be one of {sorted(_VALID_KINDS)!r}, got {kind!r}")

    progress = make_progress(ctx, lesson_id=lesson_id)
    await progress.emit(phase="kind_resolved", pct=0.0, data={"kind": kind})

    db: Database = ctx["db"]
    data_dir: DataDir = ctx["data_dir"]
    model_client = ctx["model_client"]

    lesson_graph = await db.get_lesson_graph(lesson_id)
    if lesson_graph is None:
        raise ValueError(f"lesson not found: {lesson_id!r}")

    concept = next(
        (c for c in lesson_graph.concepts if c.id == concept_id),
        None,
    )
    if concept is None:
        raise ValueError(
            f"concept {concept_id!r} not found in lesson {lesson_id!r}"
        )

    faithfulness = SourceFaithfulnessValidator()

    if kind == "mnemonic":
        gen = MnemonicGenerator(
            model_client=model_client,
            faithfulness_validator=faithfulness,
        )
        result = await gen.generate(concept, lesson_graph)
        content = result.text
    elif kind == "relevel":
        profile = await db.get_profile(profile_id)
        if profile is None:
            raise ValueError(f"profile not found: {profile_id!r}")
        gen_relevel = ReLeveler(
            model_client=model_client,
            faithfulness_validator=faithfulness,
        )
        content, _ = await gen_relevel.relevel(concept, profile, lesson_graph)
    else:  # replace
        profile = await db.get_profile(profile_id)
        if profile is None:
            raise ValueError(f"profile not found: {profile_id!r}")
        gen_replace = ExampleReplacer(
            model_client=model_client,
            faithfulness_validator=faithfulness,
        )
        records = await gen_replace.replace(concept, profile, lesson_graph)
        content = "\n\n".join(r.replacement_text for r in records)

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
    result = {"asset_id": asset_id, "file_path": str(file_path)}
    return await progress.done(result)
