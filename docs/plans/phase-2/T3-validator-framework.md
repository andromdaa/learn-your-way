# T3 — Validator Framework: ValidationResult, Validator Protocol, Gating (ADR-0011)

## Status

- [ ] T3: Validator framework

## Goal

Define the cross-cutting contract that every phase-2 validator
implements. A `Validator[T]` Protocol with a single
`validate(payload: T) -> ValidationResult` method. A `ValidationResult`
frozen dataclass carrying `passed: bool`, `reason: str | None`, and
`evidence: list[SourceSpan] | None`. A `run_validators` helper that
runs a list of validators against a payload and raises `ValidationError`
with all failed reasons if any fail. Write ADR-0011 recording the
framework design.

All validators are synchronous; the async generators call them inline
before returning.

## Files

- Create `src/lyw_core/validators/__init__.py`.
- Create `src/lyw_core/validators/base.py`.
- Create `docs/adr/0011-validator-framework.md`.
- Create `tests/unit/test_validators_base.py`.

## Depends On

- None. Can run in parallel with T0c-r1, T0c-r2, and T1.

## Acceptance

- `ValidationResult` is a `@dataclass(frozen=True)` with `passed:
  bool`, `reason: str | None`, `evidence: list[SourceSpan] | None`.
- `Validator[T]` is a `Protocol` — `def validate(self, payload: T) ->
  ValidationResult: ...`
- `run_validators(validators: Sequence[Validator[T]], payload: T) ->
  None` raises `ValidationError(reasons: list[str])` if any validator
  returns `passed=False`; succeeds silently when all pass.
- `ValidationError` is a typed exception carrying `reasons: list[str]`.
- Tests: all-pass, single-fail, multi-fail; `ValidationError` message
  lists all failed reasons.
- `ruff check`, `mypy` (strict), `pytest` all pass. ADR-0011 committed.

## Out of Scope

- Concrete validators (T4, T6, T10).
- Async validators.
- Integration with generators (T5+).

## Risk Notes

- `Validator[T]` is generic. Under `mypy --strict` with
  `no_implicit_reexport = true`, the Protocol must be exported
  explicitly from `validators/__init__.py`. Verify generic Protocol
  syntax compiles before writing downstream validators.
