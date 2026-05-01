"""Arq personalize_concept job: generate and persist a derived asset."""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from lyw_core.assessment.mnemonic import MnemonicGenerator
from lyw_core.worker.jobs._progress import make_progress
from lyw_core.db.dao import LESSON_SCOPED_CONCEPT_ID, Database, DerivedAsset
from lyw_core.modalities.mindmap import MindMapGenerator
from lyw_core.modalities.slides import SlideGenerator
from lyw_core.modalities.timeline import TimelineGenerator, TimelineSkipped
from lyw_core.personalization.relevel import ReLeveler
from lyw_core.personalization.replace import ExampleReplacer
from lyw_core.storage.fs import DataDir
from lyw_core.validators.base import run_validators
from lyw_core.validators.faithfulness import SourceFaithfulnessValidator
from lyw_core.validators.mindmap import MindMapValidator
from lyw_core.validators.timeline import TimelineValidator

_logger = structlog.get_logger(__name__)

_VALID_KINDS = frozenset(
    {"relevel", "replace", "mnemonic", "mind_map", "timeline", "slides"}
)


async def personalize_concept(
    ctx: dict[str, Any],
    *,
    lesson_id: str,
    concept_id: str,
    profile_id: str,
    kind: str,
) -> dict[str, Any]:
    """Generate and persist a derived asset.

    Parameters
    ----------
    lesson_id:
        The LessonGraph id.
    concept_id:
        The ConceptNode id within that lesson, or ``LESSON_SCOPED_CONCEPT_ID``
        (``"__lesson__"``) for lesson-level generator kinds (``mind_map``,
        ``timeline``).
    profile_id:
        The LearnerProfile id.
    kind:
        One of ``"relevel"``, ``"replace"``, ``"mnemonic"``, ``"mind_map"``,
        ``"timeline"``, or ``"slides"``.

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

    if kind == "mind_map":
        from lesson_graph.models import PersonalizationProfile

        learner_profile = await db.get_profile(profile_id)
        if learner_profile is None:
            raise ValueError(f"profile not found: {profile_id!r}")
        # Construct the generator-facing PersonalizationProfile from the
        # LearnerProfile stored in the DB.  MindMapGenerator does not currently
        # use the profile (pure graph-to-Mermaid), but the parameter is kept
        # for API parity with future modality generators.
        profile_obj = PersonalizationProfile(
            grade_level=learner_profile.grade_level,
            interests=learner_profile.interests,
        )
        gen_mm = MindMapGenerator()
        mermaid = gen_mm.generate(lesson_graph, profile_obj)
        run_validators([MindMapValidator()], mermaid)
        content = mermaid
        file_path = data_dir.write_asset(content.encode(), suffix=".mmd")
        effective_concept_id = LESSON_SCOPED_CONCEPT_ID
    elif kind == "timeline":
        from lesson_graph.models import PersonalizationProfile

        learner_profile = await db.get_profile(profile_id)
        if learner_profile is None:
            raise ValueError(f"profile not found: {profile_id!r}")
        profile_obj = PersonalizationProfile(
            grade_level=learner_profile.grade_level,
            interests=learner_profile.interests,
        )
        gen_tl = TimelineGenerator()
        tl_result = gen_tl.generate(lesson_graph, profile_obj)
        if isinstance(tl_result, TimelineSkipped):
            _logger.info(
                "timeline_skipped",
                lesson_id=lesson_id,
                profile_id=profile_id,
                reason="no_temporal_metadata",
            )
            return {"skipped": True, "reason": "no_temporal_metadata"}
        # Non-skip path: validate and persist.
        run_validators([TimelineValidator()], tl_result.mermaid)
        file_path = data_dir.write_asset(tl_result.mermaid.encode(), suffix=".mmd")
        effective_concept_id = LESSON_SCOPED_CONCEPT_ID
    elif kind == "slides":
        import dataclasses
        import json as _json

        from pydantic import BaseModel as _BaseModel

        from lesson_graph.models import PersonalizationProfile

        learner_profile = await db.get_profile(profile_id)
        if learner_profile is None:
            raise ValueError(f"profile not found: {profile_id!r}")
        profile_obj = PersonalizationProfile(
            grade_level=learner_profile.grade_level,
            interests=learner_profile.interests,
        )
        gen_slides = SlideGenerator()
        deck = await gen_slides.generate(lesson_graph, profile_obj, model_client)

        # dataclasses.asdict() does not recurse into Pydantic BaseModel instances
        # (SourceSpan is a Pydantic model). Use a custom encoder that calls
        # .model_dump() on any Pydantic model encountered during JSON serialisation.
        class _PydanticEncoder(_json.JSONEncoder):
            def default(self, o: object) -> object:
                if isinstance(o, _BaseModel):
                    return o.model_dump()
                return super().default(o)

        deck_json = _json.dumps(dataclasses.asdict(deck), cls=_PydanticEncoder)
        file_path = data_dir.write_asset(deck_json.encode(), suffix=".json")
        effective_concept_id = LESSON_SCOPED_CONCEPT_ID
    else:
        # Concept-level generators: look up the concept node first.
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
        effective_concept_id = concept_id

    asset_id = str(uuid.uuid4())
    asset = DerivedAsset(
        id=asset_id,
        lesson_id=lesson_id,
        concept_id=effective_concept_id,
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
        concept_id=effective_concept_id,
        kind=kind,
        profile_id=profile_id,
        file_path=str(file_path),
    )
    result = {"asset_id": asset_id, "file_path": str(file_path)}
    return await progress.done(result)
