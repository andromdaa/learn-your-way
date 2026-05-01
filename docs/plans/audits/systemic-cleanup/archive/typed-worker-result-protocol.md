# Initiative — Typed Worker-Result Protocol

## Status

**Shipped** (2026-05-01, AND-33, step 5/5 of the strip-in-place sequence).

See `docs/adr/0017-worker-result-contract.md` for the permanent record of
what was decided and why. The audit document below is retained as historical
context; the initiative is closed.

---

## Goal

Generators inside `personalize_concept` never raise arbitrary `Exception` subclasses across the worker→Redis→API boundary. Failure becomes a typed result envelope — for example `JobOutcome[T]` with a success-with-payload variant and a failure-with-typed-reason variant — serialized as a regular dataclass or Pydantic model. The endpoint at `src/lyw_core/api/routes/generate.py:108-122` reads `info.result` as a discriminated union, never as an exception.

## Why now

Issues #82, #83, and #84 share a shape: a custom `__init__` whose positional arity differs from `super().__init__(<msg>)`. Arq's pickle reconstructor calls `__init__(*self.args)` — only the formatted message string — then `__init__` raises `TypeError`, which Arq wraps as `DeserializationError`, which the FastAPI route does not catch, surfacing as a 500.

The point-fix (`__reduce__`) works for known exceptions, but every future generator that adds a typed exception is a fresh opportunity to forget. Slides already has three direct raises at `src/lyw_core/modalities/slides.py:153,173,176`; more arrive with each Phase 3 task. The contract should be "don't raise across the boundary," not "remember to add `__reduce__`."

The gap was invisible in code review because the existing failed-job tests at `tests/unit/test_api_generate.py:381-458` use Pydantic's `ValidationError` — not the custom `lyw_core.validators.base.ValidationError` — a coincidental name collision that makes the test appear to cover the custom exception when it does not (#84 documented this explicitly).

## What shipped in AND-33

- `src/lyw_core/worker/result.py` — `Success[T]` and `Failure` Pydantic models.
- `personalize_concept` returns `Success | Failure`; catches `ReplaceSourceTooThinError`, `OllamaError`, `ValidationError` (and structural errors) at the job boundary.
- `GET /lessons/{id}/generate/{job_id}` reads `info.result` as a discriminated union.
- `__reduce__` overrides removed from `ValidationError`, `ReplaceSourceTooThinError`, `OllamaError`.
- `LESSON_SCOPED_CONCEPT_ID` removed from `dao.py`.
- Tests updated: pickle round-trip test added; name-collision gap closed; typed `Failure` variants explicitly tested.
- ADR-0011 amended; ADR-0013 amended; ADR-0017 created.

## Closing condition

This initiative's audit directory (`docs/plans/audits/systemic-cleanup/`) may
be retired or archived after AND-33 merges. Initiative 3 (chunker contract
redefinition) remains open as a separate, independent track.
