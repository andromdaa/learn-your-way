# Example: Typical phase retrospective

A representative phase-1 retrospective showing the five required sections populated. Use as a shape reference; actual content will differ.

## What good content looks like

The example below is illustrative — adapt to your actual phase. Note the specificity throughout: file names, T-numbers, ADR numbers, concrete failure modes, named carry-overs. None of "things went well overall."

## Example file: `docs/plans/phase-1-retrospective.md`

```markdown
# Phase 1 retrospective — Ingest and ground

## What shipped

All ten deliverables from `specs/phase-1-ingest.md` landed. The Docling parser
produces `ParsedDocument` instances with page and character offsets verified by
the round-trip span verifier (T3). The heuristic chunker (T6) and LLM-refined
chunker (T7) together produce `ConceptNode` instances with non-empty source
spans. Hybrid retrieval is functional: BM25 (T8), Qdrant dense (T9), and
cross-encoder reranking (T10) run in sequence behind a single retriever
interface. The inspection CLI `python -m lyw_core inspect <pdf>` produces a
diffable concept tree against the OpenStax fixture. SQLite schema and the local
data directory are in place. `docker-compose.yml` brings up Qdrant and Redis.
`POST /sources` accepts uploads and dispatches an Arq job that produces a
parsed lesson graph; `GET /lessons/{id}` returns it.

The acceptance criterion ("100% of `ConceptNode.source_spans` resolve to valid
character offsets") holds against the OpenStax fixture and against five
additional textbook chapters used during development. The synthetic fixture
generator (`tests/fixtures/synthetic_chapter.py`) produces a 2-page PDF that
exercises the CI path without requiring the OpenStax binary; the OpenStax
fixture is gated behind `pytest -m integration`.

## Decisions that changed the spec

T7 added a required `provenance: Literal["heuristic", "llm_refined"]` field to
`ConceptNode` (ADR 0008). The spec did not anticipate this; downstream code
needs to distinguish placeholder nodes (produced by the heuristic chunker) from
refined nodes. Phase 2 generators must set `provenance="personalized"` or a
similar value when producing personalized projections — this implies a phase-2
schema change to extend the Literal, deferred to phase-2 planning.

The package layout split into `src/lesson_graph/` (canonical schema only) and
`src/lyw_core/` (everything else: parser, chunker, retrieval, CLI, adapters)
per ADR 0006. The original spec assumed a single package. The split was made
during T2 planning to preserve the schema-guard hook's narrow scope. All
phase-2 and phase-3 work inherits this layout.

The CLI ships as `python -m lyw_core` rather than a `[project.scripts]` entry
point. The wheel surface stays narrow until shipping to a second machine
becomes a real requirement. This is recorded in the T11 task file but
deserves callout here because the next phases must continue the convention.

The synthetic-PDF generator pattern (committed Python that produces a small
PDF at test time) is now the convention for any test that needs a PDF
fixture. Real-world fixtures (OpenStax) stay behind `pytest -m integration`
and are not committed.

## What was harder than expected

T7 (LLM-refined chunker) took three sessions instead of one. The first
session produced a chunker that cited spans the parser had not extracted —
the model invented page/offset pairs. The fix was to constrain the prompt
to choose from a passed-in list of candidate spans rather than emit free-form
references, and to add a validator that rejects any node whose spans are not
in the candidate set. This pattern (constrain to enum, validate to reject)
is recommended for any phase-2 LLM-driven generator.

T9 (Qdrant integration) took two sessions because the testcontainers Qdrant
image's startup time made the integration test suite painful to iterate on.
The fix was a session-scoped pytest fixture that brings Qdrant up once per
test session. Phase 2 should adopt the same pattern for any new external
service.

T10 (cross-encoder reranker) revealed that `sentence-transformers` import is
slow enough to noticeably affect test collection time. Lazy-imported the
reranker module per ADR 0007's note. Phase 2 should follow the lazy-import
convention for any heavy ML dependency.

## What was easier than expected

T1 (data directory + filesystem adapter) closed in under an hour. The
TDD-strict split was useful but the implementation was straightforward
once the tests pinned the contract. Future filesystem-adjacent work can use
this as the granularity reference.

The model-client Protocol established in phase-0 carried phase 1 with no
changes. The Ollama implementation in T7 was the first concrete client and
satisfied the Protocol on first attempt. Phase 2 can add an
OpenAI-compatible client without revisiting the Protocol.

The `SCHEMA_CHANGE=1` hook caught two unintended schema edits during the
phase (one in T6 where the agent tried to add a debug field; one in T9
where the agent attempted to add a `vector_id` to `SourceSpan`). The hook
worked exactly as designed; no false positives.

## Carry-overs

- **`personalization_profile: dict[str, Any]` schema tightening** — deferred
  TODO from `docs/02-data-model.md`. Must land in phase-2 as a SCHEMA_CHANGE=1
  task before any personalization generator ships. Schedule as `T0c-r1` in
  phase-2 planning.

- **`provenance` enum extension** — when phase-2 generators produce
  personalized nodes, the `provenance` Literal needs a new value (likely
  `"personalized"`). This is a small SCHEMA_CHANGE=1 batch alongside the
  `personalization_profile` work; consider combining into one ADR.

- **Mnemonic persistence shape** — phase-1 spec did not address mnemonics;
  phase-2 spec lists them as a deliverable but does not specify persistence.
  Decision deferred to phase-2 planning: either generate-on-demand
  (`MnemonicResult` in `lyw_core`, no schema entry) or extend
  `DerivedAsset.kind`. Recommend the former for phase 2; revisit in phase 3.

- **Cross-encoder reranker model choice** — pinned to
  `ms-marco-MiniLM-L-6-v2` (ADR 0001) without benchmarking. Performance is
  acceptable on the OpenStax fixture but has not been measured against
  realistic phase-2 query patterns. Add a phase-2 task to benchmark and
  potentially upgrade.

- **Worker error handling** — Arq integration in T12 ships happy-path only.
  A failed parse leaves the source in `parsing` status indefinitely. Add a
  phase-2 (or phase-3) task to introduce a retry policy and a failed-job
  cleanup mechanism.

- **OpenStax licensing audit** — `docs/05-privacy-legal.md` was created as a
  stub during phase-1 to satisfy the dangling reference in
  `tests/fixtures/README.md`. The actual licensing content has not been
  written. Either complete it before shipping any non-personal use of the
  system, or rescope `tests/fixtures/README.md` to drop the reference.
```

## Notes on the example

The carry-overs section is the longest by design. Carry-overs are the section the next phase's planner reads most carefully and must not miss.

"What was easier than expected" is genuinely useful — it's where the next phase loosens discipline that overshot. Without it, every phase inherits every constraint of the prior phase whether or not the constraint earns its weight.

The "Decisions that changed the spec" section is precise about ADR numbers and T-numbers because the next planner will follow those references. Vague references waste planner time.

Nothing in the example praises the team or summarizes feelings. The retrospective is a technical record. Sentiment belongs in conversation, not in the file.
