# Example: Decomposition with schema-change tasks

Some phases require changes to `src/lesson_graph/models.py`. Schema changes are protected by the `SCHEMA_CHANGE=1` hook and have non-negotiable propagation requirements. This example covers the planning-side discipline; the execution side belongs to the `run-task` skill.

## When schema changes appear in a phase

Common triggers:

- A new generator needs a field the schema does not yet carry (e.g. `provenance`, `bloom_level`).
- A deferred TODO from a prior phase comes due (e.g. `personalization_profile` tightening).
- A new modality kind needs to be added to `DerivedAsset.kind`.
- A docstring clarification on existing fields that codifies a convention (e.g. "list-order = priority").

The first three are real schema changes. The fourth is a docstring-only edit that may or may not require `SCHEMA_CHANGE=1` depending on hook strictness — check the hook config when planning.

## Task naming

Schema-change tasks are scheduled as `T0c-r<N>` (continuing the carry-over numbering from the previous phase) when they unblock subsequent feature tasks. Number monotonically across the phase regardless of which prior phase introduced the deferral.

## Required files in EVERY schema-change task

The "Files created or modified" section of any schema-change task must list at minimum:

1. **`src/lesson_graph/models.py`** — the schema edit itself.
2. **`tests/test_lesson_graph.py`** — locks the new invariants. Positive test for new field, negative test rejecting invalid values, confirmation that existing tests still pass with the new defaults.
3. **`docs/02-data-model.md`** — the data-model doc reproduces the schema and documents invariants. New fields must appear in the "Core types" code block AND in the "Invariants" section.
4. **`docs/adr/<next-number>-<slug>.md`** — one ADR per logically-related batch of changes. Multiple field additions on the same type ship in one session with one ADR containing one section per field.
5. **`docs/04-api.md`** — audit explicit. Either the OpenAPI stub mirrors the schema and is updated, OR the audit result is recorded in the task file as "no API surface change required because [reason]."

A schema-change task listing fewer than five files is incomplete. Surface this as a hard rule in the task's risk notes if helpful, but enforce it at planning time.

## Batching rule

Two or more field additions to the same type in the same phase: ONE schema-change task, ONE session, ONE ADR with one section per field. Do not split.

A field addition AND an unrelated field addition on a different type: TWO schema-change tasks. Different cognitive units, different test surfaces, and the ADRs document orthogonal decisions.

A field addition AND an enum extension: depends. Same type and same logical motivation? Batch. Different concerns? Split.

## Server-side-only fields

Some schema fields exist on the canonical type but must not appear in any API response. Examples: `correct_answer` on `AssessmentItem` (leaks the answer key). When planning a schema change that adds a server-side-only field:

- The audit of `docs/04-api.md` must explicitly note the field is server-side only.
- The task file's acceptance criterion must include: "any future API response constructed from [type] uses a separate response model that omits [field]; do not use `model_dump(exclude={...})` because exclude-by-name is silent on rename."
- This convention is recorded in the ADR.

## Example task entry (illustrative)

```markdown
## T0c-r3 — AssessmentItem fields: correct_answer, bloom_level

**Goal:** Add `correct_answer: str | None` and `bloom_level: Literal[...] | None`
to `AssessmentItem` before T8 begins. Both fields are required by phase-2
generators and validators. Single session, SCHEMA_CHANGE=1, single ADR with
two sections.

**Files created or modified:**
- modify `src/lesson_graph/models.py` — add both fields
- modify `tests/test_lesson_graph.py` — positive tests for both, negative test
  for unknown bloom_level, confirm defaults
- modify `docs/02-data-model.md` — Core types and Invariants sections
- create `docs/adr/0009-assessmentitem-fields.md` — ADR with section per field
  plus a note on the prerequisites docstring clarification (Q6)
- modify `src/lesson_graph/models.py` (docstring on ConceptNode.prerequisites
  documenting list-order = priority)
- audit `docs/04-api.md`: AssessmentItem is deliberately absent from the
  OpenAPI components. correct_answer is server-side only and must not appear
  in any response. bloom_level has no API surface relevance. Audit result
  recorded in this task file under "Decisions made" when the task closes.

**Depends on:** none (carry-over).

**Acceptance:**
- `uv run pytest tests/test_lesson_graph.py -v` green.
- `uv run mypy` green (strict).
- `docs/02-data-model.md` Core types code block matches the actual schema
  literally (compare via diff).
- ADR 0009 is committed and indexed in `docs/adr/README.md`.

**Out of scope:**
- T8's MCQ generator (depends on this task but is its own session).
- Any UI or API surface change.
- Renaming or restructuring AssessmentItem beyond the two field additions.

**Risk notes:**
- The bloom_level Literal must enumerate all six Bloom's taxonomy levels;
  partial enumeration creates false negatives in the active-learning
  validator. ADR section on bloom_level must justify the full enumeration.
- AssessmentItem is referenced indirectly by AttemptFeedback in the OpenAPI
  stub; verify the audit is honest.
```

## What the planner must NOT do

- Suggest collapsing the schema change into the task that needs the field. ("Just add it as part of T8.") Schema changes are their own session because the propagation surface is large and the SCHEMA_CHANGE=1 hook gates it deliberately.
- Suggest skipping the ADR because "it's a small change." Every schema change has an ADR. The cost is fifteen minutes; the benefit is permanent.
- Use `model_dump(exclude={"correct_answer"})` patterns in the task description. The convention is "separate response model." Surface it explicitly.
- List four files instead of five. If `docs/04-api.md` is missing from the file list, the audit hasn't been considered.

## What the planner SHOULD surface as open questions

- "Does adding [field] require any change to existing call sites that construct [type]?" If yes, the task scope expands or splits.
- "Is the audit of `docs/04-api.md` truly clean, or is the OpenAPI stub silently out of date?" Verify by comparing schema components to actual usage.
- "Does the docstring clarification on [field] count as a schema change under the current hook?" If unclear, batch it with another schema change to be safe.
