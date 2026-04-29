# T5 — Re-leveling Generator (Immersive Text, Snapshot Tests)

## Status

- [ ] T5: Re-leveling generator

## Goal

Build `ReLeveler` in `lyw_core/personalization/relevel.py`. Takes a
`ConceptNode` and a `LearnerProfile` and uses the `ModelClient` to
rewrite the concept's summary to the target reading grade. Returns the
re-leveled text and a `PersonalizationProfile` whose `replacements`
list contains one `ReplacementRecord` (original span = the concept's
first source span, replacement text = re-leveled text, justification =
"re-leveled to grade N").

Source faithfulness validator gates the result; `ValidationError`
propagates if it fails.

Unit tests mock the `ModelClient`. Real Ollama calls go in
`tests/integration/` behind `@pytest.mark.integration`.

## Files

- Create `src/lyw_core/personalization/__init__.py`.
- Create `src/lyw_core/personalization/relevel.py`.
- Create `src/lyw_core/personalization/prompts/relevel.py`.
- Create `tests/unit/test_relevel.py`.

## Depends On

- T0c-r1 (`PersonalizationProfile` and `ReplacementRecord` must exist).
- T1 (`LearnerProfile` must exist).
- T4 (source faithfulness validator gates output).

## Acceptance

- `ReLeveler(model_client: ModelClient,
  faithfulness_validator: SourceFaithfulnessValidator)` class.
- `.relevel(concept: ConceptNode, profile: LearnerProfile,
  lesson_graph: LessonGraph) -> tuple[str, PersonalizationProfile]`
  returns `(re_leveled_text, profile)`.
- Prompt instructs the model to preserve facts, terminology, and
  structure; only sentence complexity and word choice may change;
  grade target is injected from `profile.grade_level`.
- Unit test: mocked `ModelClient` returns fixed text; syrupy snapshot
  asserts the shape and field values of the returned
  `PersonalizationProfile` (replacements list length = 1,
  `justification` non-empty, `original_span` matches concept's first
  span).
- `ValidationError` is raised and propagates when faithfulness fails.
- `ruff check`, `mypy`, `pytest` all pass.

## Out of Scope

- Adaptability validator (T6 wires in after T5 is done).
- Example replacement (T7).
- Writing the DerivedAsset to the filesystem (caller's responsibility;
  see risk note).
- Combining re-leveling with example replacement into a single call.

## Risk Notes

- `DerivedAsset.uri` points to a filesystem path. The generator
  returns `(text, profile)` and does not write to disk; the caller
  (API route or Arq worker) is responsible for persisting the text via
  `lyw_core.storage.fs` and constructing the `DerivedAsset`. This is
  the correct layering — note it in the module docstring.
- Open question Q5 (worker integration) should be resolved before T5
  begins so the intended call site is known and the generator's
  signature can be validated against it.
