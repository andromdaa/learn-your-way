# T0c-r1 — Add "mnemonic" to DerivedAsset.kind Pydantic Literal

## ID and one-line summary

T0c-r1: Close the typing inconsistency between the Pydantic `DerivedAsset.kind`
Literal and the DAO that already persists mnemonics (`SCHEMA_CHANGE=1`).

## Goal

The `personalize_concept` Arq job already persists mnemonics via the DAO
(`_VALID_KINDS` includes `"mnemonic"`, `save_derived_asset` is called). What
is missing is that `lesson_graph.models.DerivedAsset.kind` (the Pydantic
model) does not include `"mnemonic"` in its Literal — only
`"immersive_text"`, `"slides"`, `"mind_map"`, `"timeline"`, `"image"`. This
is a typing inconsistency between the Pydantic model and the DAO dataclass.
This task closes it by adding `"mnemonic"` to the Pydantic Literal.

The `quiz_id` / Glows-Grows carry-over is **not** accepted debt in phase 3;
it is implemented by T0c-r3 and T0c-r4.

This task exists so that T1 and all subsequent feature tasks start from a
clean slate with no type-system inconsistencies.

## Files created or modified

- `src/lesson_graph/models.py` — **modify** (`SCHEMA_CHANGE=1`): add
  `"mnemonic"` to the `DerivedAsset.kind` Literal.
- `tests/unit/test_lesson_graph.py` — **modify**: add a test asserting
  `DerivedAsset(kind="mnemonic", ...)` is valid.
- `docs/02-data-model.md` — **modify**: add `mnemonic` to the
  `DerivedAsset.kind` enumeration description.
- `docs/plans/phase-2-retrospective.md` — **modify**: correct the
  `MnemonicResult` carry-over entry to reflect that DAO persistence already
  works and this task closes the Pydantic type gap. Correct the `quiz_id`
  entry to reflect that T0c-r3 + T0c-r4 implement it rather than deferring.

## Depends on

None.

## Acceptance

```
SCHEMA_CHANGE=1 uv run pytest --cov
```

Must exit 0 with coverage ≥ 93 %. The new Literal test in
`tests/unit/test_lesson_graph.py` must pass. CI must be green.

## Out of scope

- Implementing `quiz_id` or Glows-Grows in the API response (T0c-r3, T0c-r4).
- Any changes to the SQLite `derived_assets` schema (the DAO already accepts
  `kind="mnemonic"`).
- Adding TODO comments for phase-4 work — the carry-over is being
  implemented in phase 3, not deferred.

## Risk notes

The `SCHEMA_CHANGE=1` env var is required for the `models.py` edit; the
pre-commit hook will reject the edit without it.
