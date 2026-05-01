# Initiative — Chunker Contract Redefinition

## Goal

`HeuristicChunker.chunk` is replaced or fronted by a stage whose contract is "emit pedagogical units," not "split on Docling block-type boundaries." A successful chapter-PDF run produces 10-30 concepts, each with a teachable summary; downstream generators no longer need post-hoc thin-source guards.

## Why now

Issues #75, #76, #77, and the audit's residue all share a root: `HeuristicChunker._split_into_sections` (`src/lyw_core/chunker/heuristic.py:105-119`) treats Docling's structural signals as pedagogical signals. The 2026-05-01 audit produced 123 concepts from one chapter PDF (10-30 expected); titles like `'Algebraic'`, `'Graphical'`, `'Numeric'`, `'Technology'` (table column headers) and `'Caroline is a full-time college student planning…'` (word-problem prompt) were promoted to concepts.

Each fix has extended the post-hoc cleanup rather than moving the contract upstream:

- Deny-list at `src/lyw_core/chunker/heuristic.py:14-29` (scaffolding patterns).
- 120-char body floor at `heuristic.py:36`.
- Word-boundary title truncation at `heuristic.py:58-72`.
- Thin-span downstream guard at `src/lyw_core/personalization/replace.py:41-42` (`_MIN_BODY_CHARS = 200`).

Two `_MIN_BODY_CHARS` thresholds now drift between `heuristic.py:36` (120) and `replace.py:41` (200) — same name, different values, no shared constant. The chunker accepts a 120-char section the replacer immediately rejects.

`LLMRefiner` (`src/lyw_core/chunker/llm_refiner.py`) exists and has a tested prompt and `LLMRefinedPayload` schema, but is never imported — `src/lyw_core/worker/jobs/ingest.py:13,57` uses only `HeuristicChunker`. Plausible path: keep `HeuristicChunker` as a coarse pre-pass, evolve `LLMRefiner` so it can merge or drop heuristic nodes (today it is a 1:1 rewrite), adding a return shape (`merge`/`drop`/`keep_refined`) and a new prompt. Alternative: a single-stage LLM chunker from scratch over `ParsedDocument`. Evolution preserves a deterministic fallback; redesign is cleaner.

## Scope (in)

- Decide: evolve `LLMRefiner` (recommended) vs. design a fresh single-stage LLM chunker.
- Land the metric harness and a hand-graded fixture (one chapter PDF with expert-annotated concept boundaries, targeting ~20 expected boundaries).
- Replace the chunker invocation in `src/lyw_core/worker/jobs/ingest.py:57`.
- Collapse the duplicate `_MIN_BODY_CHARS` thresholds (`heuristic.py:36`, `replace.py:41`) into one shared constant, or remove them if the new chunker makes the guard unnecessary.

## Scope (out)

- Removing `HeuristicChunker` entirely (keep as fallback unless explicitly dropped after the redesign proves stable).
- Re-litigating `ConceptNode` schema (`SCHEMA_CHANGE=1` required for any schema change; none proposed here).
- Replacing Docling.
- Anything illustration-related (hard-rule-banned in phases 1-3 per `AGENTS.md`).
- The threshold-drift point-fix (`heuristic.py:36` vs. `replace.py:41`) as a standalone patch — defer and absorb into this initiative; the threshold should disappear in the redesign.

## Sub-PR breakdown

1. **Hand-graded fixture + metric harness** — One chapter PDF with expert-annotated boundaries; automation-friendly assertions: concept count 10-30; source-coverage (every body page covered by exactly one concept, chrome pages may be uncovered); title plausibility (no deny-list match, no table-column tokens, word-boundary endings); summary threshold (every summary ≥ 200 chars / 30 words so `replace.py`'s guard is defense-in-depth, not load-bearing).
2. **LLMRefiner evolution or redesign** — Based on the scope decision: extend `LLMRefiner` to support `merge`/`drop`/`keep_refined` return shapes with a new prompt, or design a fresh single-stage LLM chunker over `ParsedDocument`.
3. **Wire into ingest** — Replace `HeuristicChunker` at `src/lyw_core/worker/jobs/ingest.py:57`; update the provenance value per ADR-0008 if a new provenance token is introduced.
4. **Tune + decommission** — Calibrate metric targets against the hand-graded fixture (placeholder Jaccard target ≥ 0.7; calibrate after fixture is annotated); decommission stale heuristic guards (`heuristic.py:14-29,36,58-72`; `replace.py:41-42`) once the new chunker makes them redundant.

## Success criteria

- Chapter fixture yields 10-30 concepts.
- Source-coverage assertion passes (every body page covered by exactly one concept; chrome pages may be uncovered, list specified in the fixture).
- Every summary clears 200 chars / 30 words without `replace.py`'s guard tripping.
- Hand-graded Jaccard overlap ≥ calibrated target.

## Rough effort

Large. Multi-week, 4+ PRs. Could meaningfully delay Phase 3 if run in parallel with it.

## Risks / open questions

- **LLMRefiner evolution vs. fresh redesign.** Evolution preserves a deterministic fallback; redesign is cleaner but discards the existing tested prompt and schema. Recommendation: evolution unless the LLM-chunker scope grows to where the heuristic pre-pass adds no value.
- **Measurement target.** Is "concept count + threshold pass" sufficient, or is the hand-graded Jaccard the load-bearing signal? Automating (1)-(4) is faster; the Jaccard requires someone to annotate a fixture chapter (manual work). Recommendation: automate first, add hand-graded signal once the fixture is ready.
- **Cost.** Every ingest now calls the model N times per chunk (N may be 15-120 for a chapter PDF). Cost estimate required before wiring into production ingest.
- **Determinism.** LLM chunking is non-deterministic at temp > 0 and brittle at temp 0. Snapshot tests need structural assertions, not literal output comparisons.

## ADR impact

- **ADR-0008** (`docs/adr/0008-concept-node-provenance.md`) — may require amendment if a new provenance value is introduced (e.g. `"llm_chunked"` distinct from `"llm_refined"`). Any schema change requires `SCHEMA_CHANGE=1` and an updated test in `tests/unit/test_lesson_graph.py`.

## Cross-initiative dependencies

- Initiative 1 (CI integration coverage) should land first — the metric harness and concept-count assertion in Sub-PR 1 become CI gates only after Initiative 1 wires the integration job.
- Initiative 2 (typed worker-result protocol) should land before Initiative 3 if Phase 3 generators are shipping in parallel — reduces the chance of new pickle-bomb exceptions being introduced alongside the chunker redesign.
