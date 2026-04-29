# T6 — Adaptability Validator (Readability Scoring)

## Status

- [ ] T6: Adaptability validator

## Goal

Implement the adaptability validator: given the original text, the
re-leveled text, and the target grade level (integer), confirm that
the re-leveled text's Flesch-Kincaid Grade Level is strictly closer
to the target than the original's. Implements
`Validator[AdaptabilityPayload]`.

## Files

- Create `src/lyw_core/validators/adaptability.py`.
- Create `tests/unit/test_validators_adaptability.py`.
- Modify `pyproject.toml`: `uv add textstat` (pin minor, pre-1.0); add
  `[[tool.mypy.overrides]]` scoped to `textstat.*` (untyped stubs).

## Depends On

- T3 (validator framework).
- T5 (re-leveling generator; T5 provides the test fixture though there
  is no code import dependency).

## Acceptance

- `AdaptabilityPayload` dataclass: `original: str`, `releveled: str`,
  `target_grade: int`.
- `AdaptabilityValidator.validate(payload)` returns `passed=False` with
  a `reason` string showing measured grades when the re-leveled score
  did not move closer to the target; `passed=True` otherwise.
- Tests: one pass case (original FK grade 10, target 5, re-leveled
  grade 6 → pass); one fail case (re-leveled grade moved away from
  target → fail); edge case (original already at target → pass).
- `ruff check`, `mypy`, `pytest` all pass.

## Out of Scope

- Other readability metrics (Gunning Fog, Flesch Reading Ease, etc.).
- Per-sentence granularity.

## Risk Notes

- Uses `textstat` for Flesch-Kincaid Grade Level. Pin minor version
  (pre-1.0 API is unstable across minor bumps). Add
  `[[tool.mypy.overrides]]` with `ignore_missing_imports = true` scoped
  to `textstat.*` — the package ships no type stubs.
