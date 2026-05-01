# ADR-0011 — Validator Framework

## Status

Accepted (2026-04-30)
Amended (2026-05-01): validator semantics unchanged; job-boundary contract added (see below).

## Context

Phase 2 introduces six rubric-based validators (source faithfulness,
coverage, emphasis, adaptability, active learning, clarity of learning
intentions). Each validator gates persistence of a generator's output.
Without a shared contract, each validator would invent its own error
type, making the gating logic in generators inconsistent and untestable
in isolation.

## Decision

Define a minimal framework in `lyw_core/validators/base.py`:

- **`ValidationResult`**: a `@dataclass(frozen=True)` carrying `passed:
  bool`, `reason: str | None`, and `evidence: list[SourceSpan] | None`.
  Frozen so validators cannot mutate results after construction.

- **`Validator[T]`**: a `Protocol` with a single method
  `validate(self, payload: T) -> ValidationResult`. Structural typing
  means concrete validators do not need to inherit from a base class;
  they only need to implement the method with the correct signature.

- **`ValidationError`**: a typed `Exception` subclass carrying
  `reasons: list[str]`. Separates validation failures from unexpected
  runtime errors.

- **`run_validators`**: a generic helper that runs a sequence of
  validators, collects all failures before raising, and surfaces them
  together in a single `ValidationError`. Failing fast on the first
  error would hide downstream failures from the caller.

All validators are synchronous. Async generators call `run_validators`
inline before yielding or persisting output.

### Amendment (2026-05-01) — job-boundary contract

`run_validators` continues to **raise** `ValidationError` at the internal
generator boundary (e.g. inside `ReLeveler.relevel`). This is the correct
semantics for an internal boundary: callers see the full failure set
immediately, and no special return-type threading is required inside the
generator.

The **job boundary** — `personalize_concept` in
`src/lyw_core/worker/jobs/personalize.py` — catches `ValidationError` (and
other domain exceptions) and converts them to a typed `Failure` before
returning. No exception crosses the Arq pickle boundary. See
`docs/adr/0017-worker-result-contract.md` for the full contract.

This model is "raise internally, convert at the boundary": validators raise
`lyw_core.validators.base.ValidationError` (distinct from
`pydantic.ValidationError`) at the generator layer; the job layer converts
it to `Failure(code="validation_failed", ...)`.

## Consequences

- Every validator in T4, T6, and T10 must implement
  `validate(self, payload: T) -> ValidationResult` and nothing else.
- `run_validators` collects all failures before raising, so generators
  see the complete set of problems in one call.
- `evidence: list[SourceSpan] | None` on `ValidationResult` lets
  validators surface which spans failed the check, enabling precise
  error messages without a separate lookup.
- The `Validator[T]` Protocol is generic and contravariant in T.
  `run_validators` uses PEP 695 type parameter syntax for clean
  inference at call sites.

## Alternatives considered

**Abstract base class instead of Protocol**: Requires concrete validators
to inherit, coupling them to the framework. Protocol structural typing is
looser and easier to test in isolation. Rejected.

**Raise on first failure**: Simpler but hides downstream failures.
A generator with three failing validators would require three separate
runs to discover all problems. Rejected in favour of collect-all semantics.

**Async validators**: Not needed in phase 2; all generator payloads are
in-memory objects. Can be added later without breaking existing validators.

**`run_validators` returns a result instead of raising**: Considered in the
typed-worker-result-protocol initiative. Rejected in favour of "raise
internally, convert at the job boundary" — keeps generators simple and
avoids threading a return type through every call site inside a generator.
The conversion cost is paid once at the job layer.
