# Example: Standard phase decomposition

Walks through decomposing a phase spec end-to-end. Use as the template for any decomposition that does not have unusual constraints.

## Session start

```bash
git status                          # confirm clean
claude --model opusplan
```

`opusplan` is correct: planning is Opus's strength, and execution-time costs are zero in plan mode.

## User opens with

> Decompose phase 2.

## Skill workflow

### 1. Read

Per SKILL.md "Read first." The set is large but each file is small. Specifically:

- All files under `docs/`, `docs/adr/`, `specs/phase-1-*.md`, `specs/phase-2-*.md`
- The phase-1 tracker INDEX (not its task files)
- The phase-1 retrospective
- `pyproject.toml`, the schema, the model-client interface

Then `ls` `src/lyw_core/` and `tests/` two levels deep. The agent needs to know what's actually present, not what was promised.

### 2. Confirm understanding

Before producing a plan, the agent lists back:

> Phase 2 acceptance, in my words:
>
> 1. Learner profile data model + `POST /profiles`.
> 2. Re-leveling: every change diffable against source.
> 3. Interest-based example replacement.
> 4. Embedded MCQ questions tied to learning objectives.
> 5. Section-level quizzes with "Glows"/"Grows" feedback.
> 6. Mnemonic memory aids.
> 7. Quiz signal capture and rule-based gap detector.
> 8. `POST /attempts` and `POST /recommendations/next`.
>
> Carry-overs from phase-1 retrospective that constrain phase 2:
> - `provenance` field on `ConceptNode` (added in phase-1 T7) — phase-2 generators must set provenance correctly.
> - `personalization_profile: dict[str, Any]` is still a TODO; phase 2 must tighten it to a TypedDict.
> - The synthetic test fixture pattern from phase-1 is the convention for phase 2.
>
> Deferred decisions phase 2 must resolve or defer again:
> - None inherited.
>
> Three things I want to confirm before planning:
> Q1, Q2, Q3 — [actual ambiguities surfaced]

User answers; agent proceeds.

### 3. Decomposition

Typical phase-2 shape (illustrative):

- `T0c-r1`: tighten `personalization_profile` to TypedDict (schema change, SCHEMA_CHANGE=1, ADR, full propagation).
- `T0c-r2`: any other phase-1 carry-over.
- `T0c-r3`: schema additions (`correct_answer`, `bloom_level`) before assessment work begins.
- `T1`: learner profile model.
- `T2`: `POST /profiles` endpoint.
- `T3-T4`: re-leveling generator (split: pure generation logic, then validator).
- `T5`: interest-based example replacement.
- `T6`: adaptability validator (uses textstat).
- `T7`: source-faithfulness validator.
- `T8`: MCQ generator.
- `T9-T10`: coverage and emphasis validators (paired with quiz work).
- `T11`: section-quiz orchestration.
- `T12`: mnemonic generator (library code, no DerivedAsset entry).
- `T13`: quiz attempt recording.
- `T14`: gap detector (rule-based, TDD-strict).
- `T15`: `POST /attempts` endpoint.
- `T16`: `POST /recommendations/next` endpoint.

Count and order may differ; the shape is what matters.

### 4. Spec coverage table

Final section of the tracker. Every "Deliverables" bullet from the spec maps to one or more T-numbers. Example:

| Spec deliverable | T-numbers |
|---|---|
| Learner profile data model and `POST /profiles` | T1, T2 |
| Re-leveling | T3, T4, T6 |
| Interest-based example replacement | T5, T7 |
| Embedded MCQ | T8, T9, T10 |
| Section-level quizzes with feedback | T11 |
| Mnemonics | T12 |
| Quiz signal capture and gap detector | T13, T14 |
| `POST /attempts` and `POST /recommendations/next` | T15, T16 |

If any deliverable is uncovered, the decomposition is incomplete.

### 5. Open questions block

After the artifacts, list anything you couldn't resolve without input. For phase 2 these tend to be operational:

- Readability library: textstat vs. hand-rolled.
- Worker integration timing (this phase or next).
- Persistence shape for ephemeral assets like mnemonics.

Don't answer your own questions. Wait.

## What good looks like

- 14-22 tasks for a substantial phase. Fewer suggests bundling; more suggests over-decomposition.
- Every task file is self-contained — a single agent could execute it without reading sibling task files.
- Carry-over tasks come first.
- Schema changes are their own tasks with five+ files listed.
- The spec coverage table is complete.
- Open questions are concrete, not philosophical.

## Common mistakes to avoid

- **Bundling generator + validator + integration into one task** because they "go together." Two 200-line PRs review faster than one 400-line PR.
- **Reading prior-phase task files.** They're tens of thousands of tokens. The index and retrospective are the right level of detail.
- **Naming dependencies in the plan that aren't in `pyproject.toml`.** Surface as questions.
- **Picking sides on tradeoffs the user hasn't seen yet.** Risk notes are for tradeoffs; decisions wait for the user.
