"""Canonical lesson graph schema.

The single source of truth for the data model used across all phases.
Every generator and validator in the system operates against these
types. See docs/02-data-model.md for rationale.

Invariants:
- Every ConceptNode has at least one SourceSpan.
- Every SourceSpan resolves to valid character offsets in its
  referenced document.
- Every AssessmentItem references at least one SourceSpan.
- Every DerivedAsset references at least one concept in
  based_on_concepts.

The invariants are enforced by validators on this module and by a
round-trip test at ingest time (every character in every span must
resolve back to the source text).
"""

from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator


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
    prerequisites: list[str] = Field(default_factory=list)
    provenance: Literal["heuristic", "llm_refined"] = "heuristic"


class AssessmentItem(BaseModel):
    """A single quiz or embedded question.

    Every item carries source spans backing its rationale. Generators
    that produce items without resolvable spans must have those items
    discarded by the validator before persistence.
    """

    id: str
    kind: Literal["mcq", "matching", "short_answer", "drag_drop_timeline"]
    prompt: str
    rationale: str
    source_spans: list[SourceSpan] = Field(min_length=1)
    difficulty: Literal["easy", "medium", "hard"]


class DerivedAsset(BaseModel):
    """A modality output (slides, mind map, timeline, etc.).

    The asset records which concepts it was based on and the
    personalization profile that produced it. The actual content lives
    behind ``uri`` (local filesystem path).

    The ``image`` variant is reserved for a future illustration phase
    and is not produced in phases 1-3.
    """

    id: str
    kind: Literal[
        "immersive_text",
        "slides",
        "mind_map",
        "timeline",
        "image",
    ]
    based_on_concepts: list[str] = Field(min_length=1)
    # TODO(phase-2): replace with TypedDict per docs/02-data-model.md
    personalization_profile: dict[str, Any]
    uri: str | None = None


class LessonGraph(BaseModel):
    """The canonical lesson graph for a single source document."""

    id: str
    source_id: str
    concepts: list[ConceptNode]
