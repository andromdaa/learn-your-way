# Example: TDD-strict task (T3 — round-trip span verifier)

Use for tasks that are pure, deterministic, and have an unambiguous
contract. The split-prompt pattern prevents the agent from co-evolving
the tests and the implementation, which is how spec-incorrect code
ships under a green suite.

T3 is the canonical example: a function that takes a `ParsedDocument`
and a list of `SourceSpan` instances and asserts every character in
every span resolves back to the source. There is one right answer.

## Session start

```bash
git status
claude --model opusplan
```

## User opens with

> do T3

## Skill workflow

### 1. Read

- `AGENTS.md`
- `docs/plans/phase-1-ingest-tracker.md`
- `docs/plans/phase-1/T3-roundtrip-verifier.md`
- `specs/phase-1-ingest.md`
- `src/lesson_graph/models.py` (read-only — `SourceSpan` shape)
- T2's output (assumed shipped):
  - `src/lyw_core/parser/parsed_document.py` (read-only)
- Files T3 names:
  - `src/lyw_core/verify/__init__.py` (to be created)
  - `src/lyw_core/verify/spans.py` (to be created)
  - `tests/unit/test_span_verifier.py` (to be created)

### 2. Variant detection

- Schema change? No.
- New dependency? Adds `hypothesis` if not already present (already
  in dev deps per the C-series backlog — verify before adding).
- Real services? No.
- **TDD-strict: YES.** Split prompt.

### 3. Two-prompt protocol

The agent's plan is delivered in two halves. The first ends with
"stop and commit failing tests." The second begins after the user
explicitly says "implement."

#### Phase A — failing tests only

Plan output:

> I will write only `tests/unit/test_span_verifier.py` in this phase.
> No implementation. No `src/lyw_core/verify/` files yet.
>
> Test cases:
> - Empty span list returns success.
> - Single span exactly matching a substring returns success.
> - Span with `char_end` past document length raises
>   `SpanResolutionError`.
> - Span where `(char_start, char_end)` slice equals the recorded
>   text returns success.
> - Span where the slice does not equal the recorded text raises
>   `SpanResolutionError` with both expected and actual in the message.
> - Multi-page document, span crosses page boundary, slice resolves
>   correctly.
> - Property-based (Hypothesis): for any valid document and any
>   span constructed from a real substring of it, verification
>   succeeds. For any span with at least one off-by-one mutation,
>   verification fails.
>
> After writing the file, I will run pytest, show the raw failing
> output (ImportError or NameError on the verifier module), and stop.
> I will not implement anything until you tell me to.

User approves. Agent writes tests. Agent runs:

```bash
uv run pytest tests/unit/test_span_verifier.py -v
```

Output is shown raw. Tests fail because the module does not exist.
Agent commits:

```bash
git checkout -b feat/T3-span-verifier
git add tests/unit/test_span_verifier.py
git commit -m "test: failing tests for round-trip span verifier (T3)"
```

Agent stops. Session is in a deliberate pause.

#### Phase B — implement only

User reviews the test file. Edits if needed (`Ctrl+G` opens it in the
editor). When satisfied, user sends:

> Implement T3 to pass these tests. Do not modify any file under
> `tests/`. If a test is wrong, stop and tell me — do not edit it.

Agent now implements `src/lyw_core/verify/spans.py`. Critically: the
test file is closed for edits in this phase. If the agent finds a
test it believes is wrong, it must surface the conflict and stop, not
"fix" the test.

Agent runs after each meaningful change:

```bash
uv run pytest tests/unit/test_span_verifier.py -v
```

Shows raw output. When green, runs full CI:

```bash
uv run mypy
uv run ruff check . && uv run ruff format --check .
uv run pytest --cov
```

Commits:

```bash
git add src/lyw_core/verify/
git commit -m "feat: round-trip span verifier (T3)"
```

### 4. Why split

Without the split, the agent has both files open at once. When a test
fails, it has two repair paths: change the implementation, or change
the test. Models choose the locally-cheap path more often than is
safe, especially for properties that are slightly subtle (e.g.
character-vs-byte offsets, exclusive-vs-inclusive end indices). The
split removes one of the repair paths during implementation.

The cost is one extra approval gate per task. The benefit is that
the test file is *committed* before the implementation exists — no
later refactor can quietly weaken it without the diff being obvious.

### 5. Closeout

Tracker:
- Tick T3.
- Decisions made entry:

  > 2026-MM-DD — T3: span verifier raises `SpanResolutionError`
  > (new exception type in `lyw_core.verify.errors`) rather than
  > returning a bool. Rationale: callers need both expected and
  > actual text on failure, not just a yes/no, to surface a
  > diagnostic in the inspection CLI.

PR description names the spec deliverable: "Round-trip test: every
character in every span resolves back to the corresponding source
text."

End session. `/clear`.

## What good looks like

- Two commits at minimum: tests, then implementation. Three if a
  refactor or property-test fix is needed mid-implementation.
- The test file's git history shows it was committed before the
  implementation file existed.
- Hypothesis tests find at least one off-by-one bug during
  implementation. If they don't, either the property is too weak
  or the implementation is suspicious — investigate.
- The agent stopped at the phase boundary. If it did not — if it
  implemented in phase A despite the instruction — strengthen the
  skill's TDD wording before the next TDD-strict task.

## When NOT to use TDD-strict

Tasks where the contract is exploratory or the right output shape is
unclear. Examples:
- T11 inspection CLI (output format is an editorial choice).
- Prompt-tuning tasks (no fixed correct output).
- UI work.

For those, write tests after the shape is clear, in the same session.
The TDD split is a tool for tasks where the right answer is a fact,
not a judgment.