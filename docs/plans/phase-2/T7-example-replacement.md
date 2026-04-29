# T7 — Example Replacement Generator (Snapshot Tests)

## Status

- [ ] T7: Example replacement generator

## Goal

Build `ExampleReplacer` in `lyw_core/personalization/replace.py`.
Scans a `ConceptNode` for personalizable segments — analogies
("like a …"), illustrative scenarios ("imagine …"), and flavor-text
examples — and replaces them with interest-linked alternatives drawn
from `profile.interests`. Each replacement becomes a
`ReplacementRecord` in the caller-supplied `PersonalizationProfile`.

The prompt module (`prompts/replace.py`) defines "personalizable"
conservatively: explicit analogies and scenario text only. Definitions,
equations, named theorems, and formal proofs are never rewritten.

Source faithfulness validator gates each replacement; replacements that
fail are **discarded with a warning log**, not raised.

Unit tests mock the `ModelClient`. Real Ollama calls in
`tests/integration/` behind `@pytest.mark.integration`.

## Files

- Create `src/lyw_core/personalization/replace.py`.
- Create `src/lyw_core/personalization/prompts/replace.py`.
- Create `tests/unit/test_replace.py`.

## Depends On

- T0c-r1 (`ReplacementRecord` and `PersonalizationProfile` must exist).
- T1 (`LearnerProfile` must exist).
- T4 (source faithfulness validator gates each replacement).

## Acceptance

- `ExampleReplacer(model_client: ModelClient,
  faithfulness_validator: SourceFaithfulnessValidator)` class.
- `.replace(concept: ConceptNode, profile: LearnerProfile,
  lesson_graph: LessonGraph) -> list[ReplacementRecord]`
- Each returned `ReplacementRecord`: `original_span` is a `SourceSpan`
  within the concept's `source_spans` range; `replacement_text`
  non-empty; `justification` non-empty (e.g. "replaced analogy with
  interest: <interest>").
- Replacements failing the faithfulness validator are discarded and
  logged; no `ValidationError` raised.
- Unit test: mocked model returns two fixed replacements, one failing
  faithfulness; snapshot asserts only one record returned.
- `ruff check`, `mypy`, `pytest` all pass.

## Out of Scope

- Re-leveling (T5).
- Combining replacement output with re-leveling into a final
  `DerivedAsset` (caller's responsibility).
- Wiring into the Arq worker (phase 3; see
  `specs/phase-3-modalities.md`).

## Risk Notes

- "Personalizable segment" definition in the prompt is the hardest
  design decision. A conservative list is safer: over-restriction
  means fewer replacements but guaranteed source fidelity; over-
  permissiveness risks rewriting core content. Iterate on the prompt
  during implementation and record the final definition in the prompt
  module's docstring.
