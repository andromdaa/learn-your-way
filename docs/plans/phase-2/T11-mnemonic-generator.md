# T11 — Mnemonic Generator (Snapshot Tests)

## Status

- [ ] T11: Mnemonic generator

## Goal

Build `MnemonicGenerator` in `lyw_core/assessment/mnemonic.py`. Takes
a `ConceptNode` and generates a mnemonic memory aid (acronym, rhyme,
or association cue) for the concept's key terms. Returns a
`MnemonicResult(concept_id: str, text: str, source_span: SourceSpan)`.

Source faithfulness validator gates the result: the `source_span` must
resolve within the concept's span range. Mnemonic text is a creative
restatement, not a verbatim quote, so the faithfulness check is
span-boundary only (not content-matching).

`MnemonicResult` is a `lyw_core`-only frozen dataclass. It is not
persisted as a `DerivedAsset` in phase 2 — mnemonics are generated on
demand. Selection of which concepts to generate mnemonics for is the
**caller's responsibility**; the generator accepts any `ConceptNode`.

Unit tests mock the `ModelClient`. Real Ollama calls in
`tests/integration/` behind `@pytest.mark.integration`.

## Files

- Create `src/lyw_core/assessment/mnemonic.py`.
- Create `src/lyw_core/assessment/prompts/mnemonic.py`.
- Create `tests/unit/test_mnemonic.py`.

## Depends On

- T4 (source faithfulness validator).

## Acceptance

- `MnemonicGenerator(model_client: ModelClient,
  faithfulness_validator: SourceFaithfulnessValidator)` class.
- `.generate(concept: ConceptNode, lesson_graph: LessonGraph) ->
  MnemonicResult`.
- `MnemonicResult` is a `@dataclass(frozen=True)`:
  `concept_id: str`, `text: str`, `source_span: SourceSpan`.
- `ValidationError` propagates when the faithfulness check fails.
- Syrupy snapshot test: mocked model returns fixed mnemonic text;
  snapshot asserts `MnemonicResult` fields.
- `ruff check`, `mypy`, `pytest` all pass.

## Out of Scope

- Persisting `MnemonicResult` as a `DerivedAsset` (deferred to a later
  phase; no `DerivedAsset.kind` change needed in phase 2).
- "High-priority concept" selection (caller's responsibility).

## Risk Notes

- The faithfulness check for mnemonics is weaker than for quiz items:
  `source_span` must be valid (resolves within the concept's spans)
  but the mnemonic text is not required to be a verbatim quote. Note
  this distinction explicitly in the `MnemonicGenerator` docstring so
  future readers do not mistakenly strengthen the check.
