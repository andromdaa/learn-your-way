"""Canonical lesson graph schema.

The single source of truth for the data model used across all phases.
Every generator and validator in the system operates against these
types. See docs/02-data-model.md for rationale.

Invariants:
- Every ConceptNode has at least one SourceSpan.
- Every SourceSpan resolves to valid character offsets in its
  referenced document.
- Every DerivedAsset references at least one concept in
  based_on_concepts.

The invariants are enforced by validators on this module and by a
round-trip test at ingest time (every character in every span must
resolve back to the source text).
"""

from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator


class SourceSpan(BaseModel):
    """A character-precise reference back into a source document.

    Spans are inclusive of char_start and exclusive of char_end, matching
    Python slice semantics. Page bounds are inclusive on both ends.
    """

    doc_id: str
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)

    @model_validator(mode="after")
    def _check_ordering(self) -> Self:
        # Cross-field invariants must be checked after all fields are
        # populated; field_validator with info.data is order-dependent
        # and silently passes if field declaration order changes.
        if self.page_end < self.page_start:
            raise ValueError("page_end must be >= page_start")
        if self.char_end < self.char_start:
            raise ValueError("char_end must be >= char_start")
        return self


class ReplacementRecord(BaseModel):
    """One personalization replacement: original span, new text, and why.

    Used by personalization generators (T5, T7) to record every change
    made to source content so diffs remain auditable.
    """

    original_span: SourceSpan
    replacement_text: str
    justification: str

    @field_validator("justification")
    @classmethod
    def _justification_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("justification must not be empty")
        return v


class PersonalizationProfile(BaseModel):
    """Typed profile that replaces the dict[str, Any] placeholder.

    Carries learner attributes plus a complete audit trail of every
    replacement made by a personalization generator. ADR-0009.
    """

    grade_level: str
    interests: list[str]
    replacements: list[ReplacementRecord] = Field(default_factory=list)


class ConceptNode(BaseModel):
    """A single concept in the canonical lesson graph.

    Every node carries one or more source spans. Generators and
    validators downstream rely on this for provenance.
    """

    id: str
    title: str
    summary: str
    learning_objective: str
    source_spans: list[SourceSpan] = Field(min_length=1)
    prerequisites: list[str] = Field(
        default_factory=list,
        description="Ordered by priority; the gap detector treats index 0 as the highest-priority prerequisite.",
    )
    provenance: Literal["heuristic", "llm_refined"] = "heuristic"


class DerivedAsset(BaseModel):
    """A generator output (immersive text from relevel/replace).

    The asset records which concepts it was based on and the
    personalization profile that produced it. The actual content lives
    behind ``uri`` (local filesystem path).

    Per ADR-0016, only ``immersive_text`` remains — modality kinds
    (``mind_map``, ``timeline``, ``slides``) and Phase-2 kinds
    (``mnemonic``) were removed. Kept as a single-value Literal for
    forward-compat; step 5 may replace it with a plain ``str``.
    """

    id: str
    kind: Literal["immersive_text"]
    based_on_concepts: list[str] = Field(min_length=1)
    personalization_profile: PersonalizationProfile
    uri: str | None = None


class LessonGraph(BaseModel):
    """The canonical lesson graph for a single source document."""

    id: str
    source_id: str
    concepts: list[ConceptNode]
