# T0c-r1 — Accept phase-2 carry-over debt and resolve MnemonicResult persistence

## ID and one-line summary

T0c-r1: Formally document accepted technical debt for `quiz_id`/Glows-Grows, and decide whether `MnemonicResult` is persisted as a `DerivedAsset` in phase 3.

## Goal

Two carry-overs from the phase-2 retrospective are unresolved at phase-3 open. Neither requires implementation work on its own, but both must be explicitly resolved before feature tasks can make assumptions about the system's capabilities.

1. **`quiz_id` tracking and Glows/Grows in `AttemptFeedback`**: `POST /v1/attempts` cannot yet surface Glows/Grows feedback in the response because there is no `quiz_id` field linking an `AttemptRecord` to its parent `SectionQuiz`. Phase 3 adds no endpoint that surfaces Glows/Grows data (the spec's phase-3 deliverables are mind map, timeline, slides), so this can be accepted as explicit technical debt without a schema change. This task writes the acceptance into the tracker's "Out-of-Spec Discoveries" and into a code-level `# TODO(phase-4)` comment in the attempts route.

2. **`MnemonicResult` persistence — Pydantic Literal alignment**: The `personalize_concept` Arq job already persists mnemonics via the DAO (`_VALID_KINDS` includes `"mnemonic"`, `save_derived_asset` is called). The gap is that `lesson_graph.models.DerivedAsset.kind` (the Pydantic model) does not include `"mnemonic"` in its Literal — only `"immersive_text"`, `"slides"`, `"mind_map"`, `"timeline"`, `"image"`. This is a typing inconsistency between the Pydantic model and the DAO dataclass. This task closes it by adding `"mnemonic"` to the Pydantic Literal. Requires `SCHEMA_CHANGE=1`, a test in `tests/unit/test_lesson_graph.py` asserting the Literal accepts `"mnemonic"`, and a one-line update to `docs/02-data-model.md`.

This task exists so that T1 and all subsequent feature tasks start from a clean slate with no ambiguous inherited assumptions.

## Files created or modified

- `docs/plans/phase-3-modalities-tracker.md` — **modify**: populate "Out-of-Spec Discoveries" with both carry-overs and their disposition.
- `src/lyw_core/api/routes/attempts.py` — **modify**: add a `# TODO(phase-4): wire quiz_id for Glows/Grows in AttemptFeedback` comment at the response-construction site where `suggested_next_concept_id` is returned.
- `src/lyw_core/worker/jobs/personalize.py` — **modify**: add a `# TODO(phase-4): persist MnemonicResult to derived_assets via lesson_graph.models.DerivedAsset` comment at the mnemonic branch.
- `src/lesson_graph/models.py` — **modify** (`SCHEMA_CHANGE=1`): add `"mnemonic"` to the `DerivedAsset.kind` Literal.
- `tests/unit/test_lesson_graph.py` — **modify**: add a test asserting `DerivedAsset(kind="mnemonic", ...)` is valid.
- `docs/02-data-model.md` — **modify**: add `mnemonic` to the `DerivedAsset.kind` enumeration description.
- `docs/plans/phase-2-retrospective.md` — **modify**: correct the `MnemonicResult` carry-over entry to reflect that DAO persistence already works; this task closes the Pydantic type gap.

## Depends on

None.

## Acceptance

```
SCHEMA_CHANGE=1 uv run pytest --cov
```

Must exit 0 with coverage >= 93 %. The new Literal test in `tests/unit/test_lesson_graph.py` must pass. CI must be green.

## Out of scope

- Implementing `quiz_id` or Glows/Grows in the API response.
- Any changes to the SQLite `derived_assets` schema (the DAO already accepts `kind="mnemonic"`).

## Risk notes

The `SCHEMA_CHANGE=1` env var is required for the `models.py` edit; the pre-commit hook will reject the edit without it.
