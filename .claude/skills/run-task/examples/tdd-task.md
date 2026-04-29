# Example: TDD-strict task (T3 — round-trip span verifier)

Use for tasks that are pure, deterministic, and have an unambiguous
contract. Failing tests are committed before any implementation exists.
This prevents the agent from co-evolving tests and implementation, which
is how spec-incorrect code ships under a green suite.

T3 is the canonical example: a function that takes a `ParsedDocument`
and a list of `SourceSpan` instances and asserts every character in
every span resolves back to the source. There is one right answer.

## Session start

```bash
git status
claude
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
- **TDD-strict: YES.** Commit failing tests before implementing.

### 3. Plan (delegated to Opus subagent)

Spawn `Agent(subagent_type=Plan, model=opus)` with the task context.
The subagent returns the full test suite to write, the implementation
plan, and the verification commands. Because TDD-strict is flagged, the
plan explicitly separates the test-commit step from the implementation
step.

### 4. TDD execution

**Step 1 — write failing tests and commit:**

```bash
git fetch origin && git checkout -B feat/T3-span-verifier origin/main
```

Write `tests/unit/test_span_verifier.py` per the subagent's plan. Test
cases must include:

- Empty span list returns success.
- Single span exactly matching a substring returns success.
- Span with `char_end` past document length raises `SpanResolutionError`.
- Span where the slice does not equal the recorded text raises
  `SpanResolutionError` with both expected and actual in the message.
- Multi-page document, span crosses page boundary, resolves correctly.
- Property-based (Hypothesis): for any valid document and any span
  constructed from a real substring of it, verification succeeds. For
  any span with at least one off-by-one mutation, verification fails.

Run and show raw output:

```bash
uv run pytest tests/unit/test_span_verifier.py -v
```

Tests fail (module does not exist). Commit:

```bash
git add tests/unit/test_span_verifier.py
git commit -m "$(cat <<'EOF'
test(T3): failing tests for round-trip span verifier

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

**Step 2 — implement (test file is now closed for edits):**

Implement `src/lyw_core/verify/spans.py`. Run tests after each meaningful
change and show raw output. If a test appears wrong, surface the conflict
and stop — do not edit it. When green, run full pre-flight:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest --cov --cov-fail-under=90
```

Commit:

```bash
git add src/lyw_core/verify/
git commit -m "$(cat <<'EOF'
feat(T3): round-trip span verifier

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

### 5. Why commit tests first

Without the commit, the agent has both files open at once. When a test
fails, it has two repair paths: change the implementation, or change
the test. Models choose the locally-cheap path more often than is safe,
especially for subtle properties (character-vs-byte offsets,
exclusive-vs-inclusive end indices). The commit removes one repair path
during implementation — no later refactor can quietly weaken the test
suite without the diff being obvious in git history.

### 6. Closeout

Tracker update:
- Tick T3.
- Decisions made entry:

  > 2026-MM-DD — T3: span verifier raises `SpanResolutionError`
  > (new exception type in `lyw_core.verify.errors`) rather than
  > returning a bool. Rationale: callers need both expected and
  > actual text on failure, not just a yes/no, to surface a
  > diagnostic in the inspection CLI.

```bash
git add docs/plans/phase-1-ingest-tracker.md
git commit -m "$(cat <<'EOF'
chore(T3): tick T3 complete, add decisions to phase-1-tracker

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

Push and merge:

```bash
git push -u origin feat/T3-span-verifier
gh pr create --title "T3: round-trip span verifier" \
  --body "Covers spec deliverable: 'Round-trip test: every character in every span resolves back to the corresponding source text.' See \`docs/plans/phase-1/T3-roundtrip-verifier.md\`."
gh pr merge --squash --delete-branch
git checkout main && git pull --ff-only
```

Then run `/clear` to reset context, scan the tracker for the next `[ ]` entry, and re-invoke run-task for that T-number.

## What good looks like

- Two commits at minimum: tests, then implementation. Three if a
  fix is needed mid-implementation.
- The test file's git history shows it was committed before the
  implementation file existed.
- Hypothesis tests find at least one off-by-one case during
  implementation. If they don't, either the property is too weak
  or the implementation is suspicious — investigate.
- No edits to the test file after the first commit.

## When NOT to use TDD-strict

Tasks where the contract is exploratory or the right output shape is
unclear. Examples:
- Inspection CLI output format (editorial choice).
- Prompt-tuning tasks (no fixed correct output).
- UI work.

For those, write tests after the shape is clear, in the same session.
The TDD commit-first pattern is a tool for tasks where the right answer
is a fact, not a judgment.
