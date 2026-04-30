# 02 — Data model

## Why a canonical lesson graph

All modalities are generated from a shared intermediate representation
rather than directly from the raw PDF. This keeps modalities
semantically aligned and source-faithful.

The canonical lesson graph is that intermediate representation. Every
derived asset records the concepts and source spans it was generated
from. Every quiz item points back to the learning objective and source
evidence it assesses.

## Core types

The authoritative schema lives in `src/lesson_graph/models.py`. The
shape is reproduced here for review:

```python
from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator


class SourceSpan(BaseModel):
    doc_id: str
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)

    @model_validator(mode="after")
    def _check_ordering(self) -> Self:
        if self.page_end < self.page_start:
            raise ValueError("page_end must be >= page_start")
        if self.char_end < self.char_start:
            raise ValueError("char_end must be >= char_start")
        return self


class ReplacementRecord(BaseModel):
    original_span: SourceSpan
    replacement_text: str
    justification: str  # non-empty, enforced by field_validator


class PersonalizationProfile(BaseModel):
    grade_level: str
    interests: list[str]
    replacements: list[ReplacementRecord] = Field(default_factory=list)


class ConceptNode(BaseModel):
    id: str
    title: str
    summary: str
    learning_objective: str
    source_spans: list[SourceSpan] = Field(min_length=1)
    # Ordered by priority; index 0 = highest-priority prerequisite (ADR-0012)
    prerequisites: list[str] = Field(default_factory=list)
    provenance: Literal["heuristic", "llm_refined"] = "heuristic"  # ADR-0008


class AssessmentItem(BaseModel):
    id: str
    kind: Literal["mcq", "matching", "short_answer", "drag_drop_timeline"]
    prompt: str
    rationale: str
    source_spans: list[SourceSpan] = Field(min_length=1)
    difficulty: Literal["easy", "medium", "hard"]
    concept_id: str  # non-empty; references ConceptNode.id (ADR-0010)
    correct_answer: str | None = None  # MCQ only; None for other kinds
    bloom_level: (
        Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]
        | None
    ) = None  # set by MCQ generator; None treated as "remember" by active-learning validator


class DerivedAsset(BaseModel):
    id: str
    kind: Literal["immersive_text", "slides", "mind_map", "timeline", "image", "mnemonic"]
    based_on_concepts: list[str] = Field(min_length=1)
    personalization_profile: PersonalizationProfile  # ADR-0009
    uri: str | None = None
```

The `image` variant is reserved for a future illustration phase and is
not generated in phases 1-3. See `specs/phase-3-modalities.md`.

## Cross-field invariants

`SourceSpan` uses `model_validator(mode="after")` rather than
field-level `info.data` lookup. Field-level lookup is order-dependent:
reordering field declarations would silently allow inverted spans.
The model-level validator runs after all fields are populated and
therefore does not depend on declaration order.

The negative case is pinned by
`tests/unit/test_lesson_graph.py::test_source_span_validator_does_not_depend_on_field_order`.

## Invariants

These hold regardless of modality, generator, or pipeline phase:

- Every `ConceptNode` has at least one `SourceSpan`.
- Every `SourceSpan` resolves to valid character offsets in its
  referenced document, and `page_end >= page_start`,
  `char_end >= char_start`.
- Every `AssessmentItem` carries a non-empty `concept_id` referencing a
  `ConceptNode.id` in the same lesson graph (ADR-0010), and at least one
  `SourceSpan`. The cited spans must be a subset of the parent concept's
  span range.
- `AssessmentItem.correct_answer` is MCQ-specific. Generators for
  other item kinds (`short_answer`, `matching`) may leave it `None`.
  The `POST /attempts` endpoint must handle `None` gracefully.
- `AssessmentItem.bloom_level` is set by the MCQ generator prompt. A
  `None` value is treated as `"remember"` (most conservative) by the
  active learning validator so that untagged items do not silently pass
  the section-quality gate.
- `ConceptNode.prerequisites` is ordered by priority. The gap detector
  treats index 0 as the highest-priority prerequisite (ADR-0012).
- Every `DerivedAsset` references at least one concept in
  `based_on_concepts`.
- `DerivedAsset.personalization_profile` is a typed `PersonalizationProfile`
  Pydantic model (ADR-0009). Every entry in `PersonalizationProfile.replacements`
  carries a non-empty `justification`; empty justifications are rejected
  by a field validator on `ReplacementRecord`.

A round-trip test runs at ingest: every character in every span must
resolve back to the source text.

## Schema change protocol

Edits to `src/lesson_graph/models.py` are blocked by a PreToolUse hook
(`.claude/hooks/guard-schema.py`) unless `SCHEMA_CHANGE=1` is set in
the agent's environment. Schema changes must:

1. Update tests in `tests/unit/test_lesson_graph.py` to lock the new
   invariants.
2. For semantically significant changes, add an ADR under
   `docs/adr/`.

The hook is enforcement, not guidance. The actual rule lives here and
in `AGENTS.md`.

## Pedagogy rubrics

Generators and validators evaluate against these rubrics: source
faithfulness, coverage, emphasis, adaptability, active learning, and
clarity of learning intentions. These are not stored in the schema;
they are encoded in the validators that gate `DerivedAsset`
persistence.
