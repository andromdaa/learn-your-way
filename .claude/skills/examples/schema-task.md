# Example: Schema-change task (T7 — provenance field on ConceptNode)

Use whenever the task requires editing `src/lesson_graph/models.py`. The
`PreToolUse` hook blocks edits to that file unless `SCHEMA_CHANGE=1` is
in the environment.

## Session start

```bash
git status
SCHEMA_CHANGE=1 claude --model opusplan
```

The env var must be set when launching Claude, not mid-session. The hook
inspects the agent's environment at every tool call.

## User opens with

> do T7

## Skill workflow

### 1. Read

- `AGENTS.md`
- `docs/plans/phase-1-ingest-tracker.md`
- `docs/plans/phase-1/T7-llm-refined-chunker.md`
- `specs/phase-1-ingest.md`
- `docs/02-data-model.md` (always read for schema changes — it documents the protocol)
- Existing schema and tests:
  - `src/lesson_graph/models.py`
  - `tests/test_lesson_graph.py`
- Files named in T7:
  - `src/lyw_core/chunker/llm_refined.py` (to be created)
  - `tests/unit/test_llm_refined_chunker.py` (to be created)
  - any prompt-template files T7 names

### 2. Variant detection

- **Schema change: YES.** ConceptNode gains a `provenance` field per
  ADR-0008.
- New dependency? No (uses existing model client Protocol).
- Real services? No (Ollama abstracted via Protocol; tests use a fake).
- TDD-strict? Partial — schema change and chunker logic are TDD;
  prompt iteration is not (prompts are tuned by inspection, not assertion).

### 3. Acceptance readback

> T7 acceptance, in my words:
>
> Schema change:
> - `ConceptNode.provenance: Literal["heuristic", "llm_refined"]` added.
> - Existing tests updated to set `provenance` on every constructed node.
> - New test: `test_concept_node_rejects_unknown_provenance`.
> - ADR-0008 added under `docs/adr/` recording the field, the
>   rationale (downstream code must distinguish placeholder from
>   refined), and the alternative considered (string-prefix sentinel
>   on `learning_objective`, rejected).
>
> Chunker:
> - LLM-refined chunker takes the heuristic chunker's output and a
>   `ModelClient`, produces refined `ConceptNode` instances with
>   `provenance="llm_refined"`.
> - Schema validation gates persistence — refined nodes that fail
>   validation are rejected, not patched.
> - Tests use a fake `ModelClient` that returns canned outputs;
>   no real model calls in tests.

### 4. Plan output

Files:
- modify `src/lesson_graph/models.py` — add `provenance` field
- modify `tests/test_lesson_graph.py` — update existing fixtures, add
  new negative test
- create `docs/adr/0008-conceptnode-provenance.md`
- create `src/lyw_core/chunker/llm_refined.py`
- create `tests/unit/test_llm_refined_chunker.py`
- modify `docs/02-data-model.md` — document the new field under "Core types"

Order:
1. Schema change first, in isolation:
   - Update `models.py`.
   - Update existing tests in `test_lesson_graph.py` so they still pass
     with the new required field.
   - Add the new negative test.
   - Run schema tests; confirm green.
   - Add ADR-0008.
   - Update `docs/02-data-model.md`.
   - Commit: `feat(schema): add ConceptNode.provenance (T7, ADR-0008)`.
2. Chunker after, on top of green schema:
   - Write failing chunker tests with a fake ModelClient.
   - Implement chunker.
   - Iterate on prompts inside the fake; do not modify tests to fit
     prompt output.
   - Commit: `feat: LLM-refined chunker producing refined ConceptNodes (T7)`.
3. Run full CI.

Do not touch:
- `AssessmentItem`, `DerivedAsset`, `SourceSpan`, `LessonGraph` — schema
  scope is one new field on one type
- The heuristic chunker (T6's territory; assumed shipped)
- Any retrieval code (T8/T9/T10)

Verification:
```bash
uv run pytest tests/test_lesson_graph.py -v       # schema first
uv run pytest tests/unit/test_llm_refined_chunker.py -v
uv run mypy
uv run ruff check . && uv run ruff format --check .
uv run pytest --cov
```

Stop. Await approval.

### 5. Hook will fire on the schema edit

When the agent attempts `Edit(src/lesson_graph/models.py)`, the hook
checks `SCHEMA_CHANGE=1` and allows. If the env var is missing, the
hook blocks with a clear message and the session must be restarted with
the variable set. Do not work around the hook; restart the session.

### 6. Closeout

Tracker update:
- Tick T7.
- Decisions made entry:

  > 2026-MM-DD — T7: ConceptNode gains `provenance` field per ADR-0008.
  > Considered: string-prefix sentinel on `learning_objective` (e.g.
  > `"[heuristic] ..."`). Rejected because string-matching is fragile
  > and the prefix bleeds into downstream prompts. The Literal field
  > is type-checked, exhaustive at match time, and free at runtime.

PR description must include:
- Spec deliverable covered ("Chunker emits ConceptNode instances ...").
- Schema change callout: "This PR adds a required field to
  `ConceptNode`. ADR-0008 documents the change. All existing tests
  updated."
- ADR link.

End session. `/clear`. The next session must NOT use `SCHEMA_CHANGE=1`
unless its task also requires it.

## What good looks like

- Schema change in its own commit, separate from the chunker.
- ADR exists before the chunker depends on the new field.
- `docs/02-data-model.md` updated in the same PR — schema docs do not
  drift from the schema.
- All existing tests still pass; new negative test pins the new
  invariant.
- Hook fired on the legitimate edit and allowed it (verify by checking
  no "blocked" messages in the session log).