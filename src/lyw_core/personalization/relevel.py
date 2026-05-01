"""Re-leveling generator: rewrites a concept summary to a target reading grade.

Returns the re-leveled text and a PersonalizationProfile recording the
replacement. Does not write to disk — the caller (API route or Arq worker)
is responsible for persisting the text via lyw_core.storage.fs and
constructing the DerivedAsset. See docs/plans/phase-2/T5-relevel-generator.md.
"""

from __future__ import annotations

from lesson_graph.interfaces import ModelClient
from lesson_graph.models import (
    ConceptNode,
    LessonGraph,
    PersonalizationProfile,
    ReplacementRecord,
)
from lyw_core.personalization.prompts.relevel import build_relevel_messages
from lyw_core.profiles.models import LearnerProfile
from lyw_core.validators.base import run_validators
from lyw_core.validators.faithfulness import (
    ItemValidationPayload,
    SourceFaithfulnessValidator,
)


class ReLeveler:
    """Rewrites a ConceptNode summary to a target reading grade.

    Source faithfulness is validated before returning: the replacement's
    original_span must fall within the concept's source spans in the
    lesson graph. ValidationError propagates to the caller.
    """

    def __init__(
        self,
        model_client: ModelClient,
        faithfulness_validator: SourceFaithfulnessValidator,
    ) -> None:
        self._model = model_client
        self._faithfulness = faithfulness_validator

    async def relevel(
        self,
        concept: ConceptNode,
        profile: LearnerProfile,
        lesson_graph: LessonGraph,
    ) -> tuple[str, PersonalizationProfile]:
        """Rewrite concept.summary to profile.grade_level.

        Returns (re_leveled_text, personalization_profile).
        Raises ValidationError if faithfulness check fails.
        """
        messages = build_relevel_messages(concept, profile)
        re_leveled_text = await self._model.complete(messages)

        original_span = concept.source_spans[0]
        replacement = ReplacementRecord(
            original_span=original_span,
            replacement_text=re_leveled_text,
            justification=f"re-leveled to grade {profile.grade_level}",
        )

        # Gate via faithfulness: verify original_span is within the concept's
        # source spans in the lesson graph (guards against stale concept refs).
        run_validators(
            [self._faithfulness],
            ItemValidationPayload(
                concept_id=concept.id,
                spans=[original_span],
                lesson_graph=lesson_graph,
            ),
        )

        personalization_profile = PersonalizationProfile(
            grade_level=profile.grade_level,
            interests=profile.interests,
            replacements=[replacement],
        )
        return re_leveled_text, personalization_profile
