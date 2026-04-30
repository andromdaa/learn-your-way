"""Mnemonic generator: produces a memory aid for a single ConceptNode.

The faithfulness check is span-boundary only — the source_span must resolve
within the concept's span range, but the mnemonic text is a creative
restatement and is not required to be a verbatim quote. ValidationError
propagates to the caller on failure (unlike the discard-on-fail approach
used by ExampleReplacer and MCQGenerator). See
docs/plans/phase-2/T11-mnemonic-generator.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from lesson_graph.interfaces import ModelClient
from lesson_graph.models import AssessmentItem, ConceptNode, LessonGraph, SourceSpan
from lyw_core.assessment.prompts.mnemonic import build_mnemonic_messages
from lyw_core.validators.base import run_validators
from lyw_core.validators.faithfulness import (
    ItemValidationPayload,
    SourceFaithfulnessValidator,
)


@dataclass(frozen=True)
class MnemonicResult:
    """A generated mnemonic memory aid for a concept."""

    concept_id: str
    text: str
    source_span: SourceSpan


class MnemonicGenerator:
    """Generates a mnemonic for a ConceptNode and validates span provenance.

    The faithfulness validator confirms source_span is within the concept's
    span range. It does NOT validate the mnemonic text content, which is a
    creative restatement of the concept rather than a verbatim quote.
    """

    def __init__(
        self,
        model_client: ModelClient,
        faithfulness_validator: SourceFaithfulnessValidator,
    ) -> None:
        self._model = model_client
        self._faithfulness = faithfulness_validator

    async def generate(
        self,
        concept: ConceptNode,
        lesson_graph: LessonGraph,
    ) -> MnemonicResult:
        """Generate a mnemonic for concept.

        Raises ValidationError if the span-boundary faithfulness check fails.
        """
        messages = build_mnemonic_messages(concept)
        text = await self._model.complete(messages)

        source_span = concept.source_spans[0]

        check_item = AssessmentItem(
            id="__mnemonic_check__",
            kind="short_answer",
            prompt=concept.summary[:200],
            rationale="faithfulness gate for mnemonic",
            source_spans=[source_span],
            difficulty="easy",
            concept_id=concept.id,
        )
        run_validators(
            [self._faithfulness],
            ItemValidationPayload(item=check_item, lesson_graph=lesson_graph),
        )

        return MnemonicResult(
            concept_id=concept.id,
            text=text,
            source_span=source_span,
        )
