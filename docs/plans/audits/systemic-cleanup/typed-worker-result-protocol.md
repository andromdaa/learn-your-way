# Initiative — Typed Worker-Result Protocol

## Goal

Generators inside `personalize_concept` never raise arbitrary `Exception` subclasses across the worker→Redis→API boundary. Failure becomes a typed result envelope — for example `JobOutcome[T]` with a success-with-payload variant and a failure-with-typed-reason variant — serialized as a regular dataclass or Pydantic model. The endpoint at `src/lyw_core/api/routes/generate.py:108-122` reads `info.result` as a discriminated union, never as an exception.

## Why now

Issues #82, #83, and #84 share a shape: a custom `__init__` whose positional arity differs from `super().__init__(<msg>)`. Arq's pickle reconstructor calls `__init__(*self.args)` — only the formatted message string — then `__init__` raises `TypeError`, which Arq wraps as `DeserializationError`, which the FastAPI route does not catch, surfacing as a 500.

The point-fix (`__reduce__`) works for known exceptions, but every future generator that adds a typed exception is a fresh opportunity to forget. Slides already has three direct raises at `src/lyw_core/modalities/slides.py:153,173,176`; more arrive with each Phase 3 task. The contract should be "don't raise across the boundary," not "remember to add `__reduce__`."

The gap was invisible in code review because the existing failed-job tests at `tests/unit/test_api_generate.py:381-458` use Pydantic's `ValidationError` — not the custom `lyw_core.validators.base.ValidationError` — a coincidental name collision that makes the test appear to cover the custom exception when it does not (#84 documented this explicitly).

## Scope (in)

- A typed `JobOutcome[T]` used by every generator inside `src/lyw_core/worker/jobs/personalize.py:69-184`.
- Refactor `ReplaceSourceTooThinError`, `OllamaError`, and `lyw_core.validators.base.ValidationError`, and the three direct raises in `src/lyw_core/modalities/slides.py:153,173,176`, into typed-failure returns.
- Update the endpoint at `src/lyw_core/api/routes/generate.py:108-122` to read `info.result` as a discriminated union.
- Update the failure-path tests at `tests/unit/test_api_generate.py:381-458` to exercise each typed-failure variant explicitly — including the custom `ValidationError` (not Pydantic's), closing the name-collision gap.
- ADR amendment for ADR-0011 (`docs/adr/0011-validator-framework.md`) changing `run_validators(...)` from raise to result-return.

## Scope (out)

- Changing how Arq itself serializes results (we live with pickle).
- Touching `src/lyw_core/worker/jobs/ingest.py` (different shape; separate initiative if needed).
- Folding `LLMRefinerError` in — only if Initiative 3 ships first and introduces it.
- The immediate `__reduce__` overrides shipping in the issue-specific PRs for #82/#83/#84 — those land in their own narrow PRs; this initiative structurally supersedes them.

## Sub-PR breakdown

1. **`JobOutcome[T]` + endpoint consumer** — Define the typed envelope; update `src/lyw_core/api/routes/generate.py:108-122` to read it as a discriminated union.
2. **Migrate replace + validators** — `ReplaceSourceTooThinError` and `lyw_core.validators.base.ValidationError` return typed failures; update dispatch at `src/lyw_core/worker/jobs/personalize.py:69-184`. File ADR-0011 amendment with or before this PR.
3. **Migrate Ollama + slides** — `OllamaError` and the three direct raises in `src/lyw_core/modalities/slides.py:153,173,176` become typed-failure returns.
4. **Cleanup + invariant check** — Decommission the `__reduce__` point-fixes; add a static or focused-unit check enforcing that workers can only fail via `JobOutcome.failure(...)`. Update `tests/unit/test_api_generate.py:381-458` to name-disambiguate the custom vs. Pydantic `ValidationError`.

## Success criteria

- `grep` shows no exception crossing the Arq boundary from any generator in `src/lyw_core/personalization/`, `modalities/`, `assessment/`, or `validators/`.
- `tests/unit/test_api_generate.py` covers every typed-failure variant explicitly; no Pydantic-vs-custom name-collision masking.
- 93% coverage gate holds.
- A static or focused-unit check enforces "workers can only fail with `JobOutcome.failure(...)`."

## Rough effort

Medium. ~2-4 PRs over ~2 weeks.

## Risks / open questions

- **Phase 3 in-flight contention.** Initiative 2 touches `personalize.py`, `slides.py`, and the modality generators — the same files Phase 3 generators are being added to. Sequencing matters; land this initiative's PRs incrementally with small diffs and keep rebasing if Phase 3 is not paused.
- **ADR-0011 amendment timing.** `docs/adr/0011-validator-framework.md` defines `run_validators(...)` as raising `ValidationError`; changing to a result-return is an ADR amendment, not a silently overturnable convention. File ADR-first (before or alongside Sub-PR 2) to keep the design conversation out of code review rather than buried in it.

## ADR impact

- **ADR-0011** (`docs/adr/0011-validator-framework.md`) — requires amendment: `run_validators(...)` will return a typed result instead of raising `ValidationError`. File as a separate PR before or alongside Sub-PR 2.

## Cross-initiative dependencies

- Depends on Initiative 1 (CI integration coverage) having landed. Without it, every migration PR here is manually verified against a real chapter — the same feedback loop the audit found inadequate.
