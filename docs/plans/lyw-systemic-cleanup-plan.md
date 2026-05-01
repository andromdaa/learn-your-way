# LYW Systemic Cleanup — Planning Draft

> **Status:** Draft for user review, 2026-05-01. No code changes until the user signs off on scope and sequencing.

## Context

The pipeline-audit run on 2026-05-01 surfaced [#82](https://github.com/andromdaa/learn-your-way/issues/82) (`ReplaceSourceTooThinError` unpicklable, 500 from `GET /lessons/{id}/generate/{job_id}`). Further inspection found the same defect class in `OllamaError` ([#83](https://github.com/andromdaa/learn-your-way/issues/83)) and `lyw_core.validators.base.ValidationError` ([#84](https://github.com/andromdaa/learn-your-way/issues/84)). The chunker false-positives that produced the thin span in the first place are a third instance of a recurring pattern.

The closed-and-recurred receipts:

| Closed by | What it fixed | What recurred |
|---|---|---|
| #66 → API | `dict(<exc>)` 500 turned into `status="failed"` envelope | #82/#83/#84 — pickle-deserialization layer never landed |
| #64 → fences | Strip ` ```json ` wrapper before `json.loads` | #77 — different silent-empty path (thin source, not bad JSON) |
| #76 → scaffolding | Deny-list + 120-char body floor | #75 (mid-word titles), #77 (thin-source flourishes) still escaped |
| #75 → titles | Word-boundary truncation | Body-fallback fired at all because chunker still emits chrome |
| #77 → guard | Raise `ReplaceSourceTooThinError` pre-flight | #82 — that very exception round-trips wrong through Arq pickle |

Every fix has been narrowly scoped (PRs #73/#74/#78/#79/#80 all explicitly say so) and each has held *for the failure mode it addressed* — but the class has not been engaged. Three structural changes would.

## Initiatives

### Initiative 1 — CI integration coverage

**Goal.** A `pytest -m integration` job in `.github/workflows/ci.yml` runs on every PR (or nightly), exercising parse → chunk → ingest → personalize → API-poll end-to-end against Testcontainers-managed Redis/Qdrant and a mock/recorded Ollama. The next chunker false-positive or worker-boundary exception is caught in CI, not by `scripts/run_pipeline.py` against a real chapter.

**Why now.** Today's CI (`.github/workflows/ci.yml:13-52`) only runs unit tests with mocked `DocumentConverter.convert` and mocked Ollama. Every issue in the recurrence table was found by a subagent running the pipeline by hand. `tests/integration/` already exists (`test_ingest_job.py`, `test_retrieval_qdrant.py`, `test_ollama_live.py`) and `testcontainers>=4.14.2` is a dev dep. The infrastructure is in place — the wiring is not.

**Scope (in).** CI job that boots Redis + Qdrant via Testcontainers and runs `pytest -m integration`. A new end-to-end test that ingests a chapter fixture and triggers one `personalize_concept` per kind, asserting `status="failed"` round-trips on a forced exception. An invariant test asserting every `Exception` subclass under `src/lyw_core/` survives `pickle.loads(pickle.dumps(...))`.

**Scope (out).** Real Ollama in CI (use a fake `ModelClient` or recorded responses; live `gemma3:4b` is a separate discussion). Coverage gates for integration tests (the 93% gate stays a unit-test gate). Re-architecting existing integration tests beyond what's needed to run them in CI.

**Success criteria.**
- A PR introducing any of #82/#83/#84 from clean main fails CI before merge.
- Integration job wall-clock under ~6 min on the GitHub-hosted runner.
- The smoke test ingests a chapter fixture and yields **between 5 and 60 concepts** (any number outside fails — captures the 369→123 regression that #76 and the audit both flagged).
- Pickle invariant test passes for every `Exception` subclass under `src/lyw_core/`.

**Rough effort.** Small to medium. Job wiring + Testcontainers fixture is small (single PR, <1 week). Meaningful end-to-end fixture + invariant test push it to medium (2 PRs, ~2 weeks).

**Risks / open questions.** Blocking PR gate vs. nightly soft-gate while flake risk is unknown. Real Ollama in CI vs. recorded fake (latter brittle to prompt drift; former slow). `tests/integration/test_ollama_live.py` already exists — clarify whether CI-runnable.

### Initiative 2 — Typed worker-result protocol

**Goal.** Generators inside `personalize_concept` never raise arbitrary `Exception` subclasses across the worker→Redis→API boundary. Failure becomes a typed result envelope (e.g. `JobOutcome[T]`: success-with-payload | failure-with-typed-reason) serialized as a regular dataclass/Pydantic model. The endpoint at `src/lyw_core/api/routes/generate.py:108-122` reads `info.result` as a discriminated union, never as an exception.

**Why now.** The bombs in #82/#83/#84 share a shape: a custom `__init__` whose positional arity differs from `super().__init__(<msg>)`. Arq's pickle reconstructor calls `__init__(*args)` with `self.args` (just the message); `__init__` raises `TypeError`; FastAPI returns 500. The point-fix (`__reduce__`) works for *known* exceptions, but every future generator that adds a typed exception (slides already has three at `src/lyw_core/modalities/slides.py:153,173,176`; more arrive with each Phase 3 task) is a fresh chance to forget. The contract should be "don't raise across the boundary," not "remember to add `__reduce__`."

**Scope (in).** A typed `JobOutcome[T]` used by every generator inside `src/lyw_core/worker/jobs/personalize.py:69-184`. Refactor `ReplaceSourceTooThinError`, `OllamaError`, `lyw_core.validators.base.ValidationError`, and the slides direct-raises into typed-failure returns. Update the endpoint and the failure-path tests at `tests/unit/test_api_generate.py:381-458` (which today coincidentally use Pydantic's `ValidationError`, masking the gap — #84 explicitly called this out).

**Scope (out).** Changing how Arq itself serializes results (we live with pickle). Touching `src/lyw_core/worker/jobs/ingest.py` (different shape, separate). Folding `LLMRefinerError` in (only if Initiative 3 ships first). The immediate `__reduce__` overrides for #82/#83/#84 — those land in their issue PRs and this initiative supersedes them.

**Success criteria.** `grep` shows no exception crossing the Arq boundary from any generator in `src/lyw_core/personalization`, `modalities`, `assessment`, `validators`. `tests/unit/test_api_generate.py` covers every typed-failure variant explicitly (no name-collision masking). 93% coverage holds. A static or focused-unit check enforces "workers can only fail with `JobOutcome.failure(...)`."

**Rough effort.** Medium. ~2-4 PRs over ~2 weeks: (1) `JobOutcome` + endpoint consumer, (2) migrate replace + validators, (3) migrate ollama + slides, (4) cleanup + invariant test.

**Risks / open questions.** Mid-flight Phase 3 work churns the same files — sequencing matters. **ADR-0011** (`docs/adr/0011-validator-framework.md`) defines `run_validators(...)` as raising `ValidationError`; changing to a result-return is an ADR amendment, not silently overturnable — flagged below. The custom `ValidationError` is also raised directly from `slides.py:153,173,176` without going through `run_validators` — migration must catch all call sites.

### Initiative 3 — Chunker contract redefinition

**Goal.** `HeuristicChunker.chunk` is replaced (or fronted) by a stage whose contract is "emit pedagogical units," not "split on Docling block-type boundaries." A successful chapter-PDF run produces 10-30 concepts, each with a teachable summary, and downstream generators no longer need post-hoc thin-source guards.

**Why now.** #75, #76, #77, and the audit's residue (table-column headers `Algebraic`/`Graphical`/`Numeric`/`Technology` promoted to four concepts; word-problem prompts as titles) are faces of one defect: `HeuristicChunker._split_into_sections` (`src/lyw_core/chunker/heuristic.py:105-119`) treats Docling's structural signals as pedagogical signals. Each fix has *extended* the post-hoc cleanup: deny-list (`heuristic.py:14-29`), 120-char body floor (`heuristic.py:36`), word-boundary title truncation (`heuristic.py:58-72`), thin-span downstream guard (`replace.py:41-42`). Two `_MIN_BODY_CHARS` thresholds now drift between `heuristic.py:36` (120) and `replace.py:41` (200), with no shared definition of "teachable."

**Is `LLMRefiner` the right substrate?** A concept-extraction LLM stage exists at `src/lyw_core/chunker/llm_refiner.py:33` with a tested prompt and `LLMRefinedPayload` schema. It is **never imported** — `src/lyw_core/worker/jobs/ingest.py:13,57` uses only `HeuristicChunker`. Plausible path: keep `HeuristicChunker` as a coarse pre-pass, evolve `LLMRefiner` so it can *merge or drop* heuristic nodes (today it's a 1:1 rewrite); this adds a return shape (`merge`/`drop`/`keep_refined`) and a new prompt. Alternative: a single-stage LLM chunker from scratch over `ParsedDocument`. First option preserves a deterministic fallback; second is cleaner. **Recommend evolution unless the user prefers the redesign.**

**How to measure "pedagogical unit" objectively.** Composite metric: (1) concept count in [10, 30] for a chapter fixture; (2) source-coverage — every body page covered by exactly one concept (chrome pages may be uncovered, spec the list); (3) title plausibility — no scaffolding-deny-list match, no table-column tokens, word-boundary endings; (4) summary teachability — every summary clears the 200-char / 30-word threshold so `replace.py`'s guard becomes defense-in-depth, not load-bearing; (5) hand-graded fixture — one chapter, expert-annotated with ~20 "right" boundaries, scored via Jaccard overlap (placeholder target ≥0.7, calibrate after fixture lands). (1)-(4) are automation-friendly; (5) is the load-bearing signal but needs manual label work.

**Scope (in).** Decide LLMRefiner-evolution vs. fresh LLM chunker. Land the metric harness + hand-graded fixture. Replace the chunker invocation in `ingest.py:57`. Collapse the duplicate `_MIN_BODY_CHARS` thresholds into one shared constant.

**Scope (out).** Removing `HeuristicChunker` (keep as fallback unless user explicitly drops). Re-litigating `ConceptNode` schema (no `SCHEMA_CHANGE=1` work). Replacing Docling. Anything illustration-related (still hard-rule-banned).

**Success criteria.** Chapter fixture yields 10-30 concepts. Source-coverage assertion passes. Every summary clears the 200-char / 30-word threshold without `replace.py`'s guard tripping. Hand-graded Jaccard ≥ chosen target.

**Rough effort.** Large. Sub-phase work, multi-week, 4+ PRs: (1) hand-graded fixture + metric harness, (2) LLMRefiner evolution or redesign, (3) wire into ingest, (4) tune + decommission stale heuristic guards. Could meaningfully delay Phase 3.

**Risks / open questions.** Cost — every ingest now calls the model N times. Determinism — LLM chunking is non-deterministic at temp >0 and brittle at 0; snapshot tests need structural assertions, not literal output. Phase 3 contention. ADR-0008 (`docs/adr/0008-concept-node-provenance.md`) may need amendment for a new provenance value.

## Sequencing recommendation

Initiative 1 first. CI integration coverage is a force multiplier — once landed, every change in Initiatives 2 and 3 is verified end-to-end before merge, eliminating the by-hand-on-a-real-chapter feedback loop that is the root cause of the recurrence cycle. It is also the smallest and most reversible. Then Initiative 2, because it unblocks Phase 3 generators from re-introducing the same bomb class. Initiative 3 last: largest, most likely to compete with Phase 3, most deserving of the safety net the others provide.

## What this plan does NOT do

- **Immediate `__reduce__` fixes for #82/#83/#84.** Point fixes ship in their own narrow PRs (sibling agents are filing them now). Initiative 2 supersedes them structurally.
- **Empty-asset write at `src/lyw_core/worker/jobs/personalize.py:181-183`.** When `replace()` returns `[]`, the orchestrator joins zero records to `""` and writes a 0-byte `.txt` (cf. #64 residue). Fold into the #82 PR or file separately — user call.
- **Threshold drift between `heuristic.py:36` (120) and `replace.py:41` (200).** Small bug, separate point-fix — or absorbed into Initiative 3, where the threshold should disappear.
- **Phase 3 modality work itself.** Ships per `specs/phase-3-modalities.md`; this plan is structural cleanup, not Phase 3 displacement.
- **Web UI / CLI / docs touches.** Out of scope.

## Open questions for the user

1. **Should the integration CI job block PRs from day one, or run nightly first?** Blocking trades CI flake risk for tighter feedback; nightly accepts ~24h of bug landing.
2. **For Initiative 3, evolve `LLMRefiner` (`src/lyw_core/chunker/llm_refiner.py:33`) or design a new LLM chunker from scratch?** Evolution preserves the deterministic fallback; redesign is cleaner. Different ADR implications.
3. **Is "concept count + threshold pass" sufficient for Initiative 3, or is the hand-graded Jaccard the load-bearing signal?** The latter requires someone to annotate a fixture chapter; the former can ship without that.
4. **Phase 3 is in flight — interrupt it, run in parallel, or wait until Phase 3 closes?** Initiative 2 in particular touches files Phase 3 generators are also touching.
5. **For Initiative 2, file an ADR amendment to ADR-0011 up front, or batch with the migration PR?** ADR-first is more deliberate; batched is faster but risks the design conversation getting buried in code review.
