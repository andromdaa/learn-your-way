# Example: Standard task (T1 — data directory layout)

This walks through a typical phase-1 task with no special variants. Use as
the template for any task that is not a schema change, does not add a
dependency, and does not touch real services.

## Session start

Clean tree. Plain invocation:

```bash
git status
claude
```

## User opens with

> do T1

## Skill workflow

### 1. Read

- `AGENTS.md`
- `docs/plans/phase-1-ingest-tracker.md` (the index)
- `docs/plans/phase-1/T1-data-directory.md`
- `specs/phase-1-ingest.md`
- Files named in T1's "Files created or changed":
  - `src/lyw_core/storage/__init__.py` (to be created)
  - `src/lyw_core/storage/filesystem.py` (to be created)
  - `tests/unit/test_filesystem.py` (to be created)
  - `pyproject.toml` (modify — add Settings field if not present)

### 2. Variant detection

- Schema change? No. `src/lesson_graph/models.py` not in file list.
- New dependency? No.
- Real services? No. In-memory only.
- TDD-strict? Yes — deterministic logic; commit failing tests before implementing.

### 3. Acceptance readback

> T1 acceptance, in my words:
>
> - A `Settings.data_dir: Path` exists and resolves to the configured
>   directory.
> - A filesystem adapter exposes `read_bytes(relative_path)`,
>   `write_bytes(relative_path, data)`, and `exists(relative_path)`,
>   all rooted at `data_dir`.
> - Path traversal outside `data_dir` is rejected with a specific
>   exception type, not silently allowed.
> - Tests cover: round-trip write/read, traversal rejection, missing-file
>   behavior, and directory creation on first write.
>
> One ambiguity: the task file says "rooted at data_dir" but does not
> specify behavior when `data_dir` itself does not exist. Should the
> adapter create it on first use, or fail loudly? I will assume create-on-first-use
> and surface this in "Decisions made" unless you say otherwise.

### 4. Plan (delegated to Opus subagent)

Spawn `Agent(subagent_type=Plan, model=opus)` with the task context above.
The subagent returns:

Files:
- create `src/lyw_core/storage/__init__.py`
- create `src/lyw_core/storage/filesystem.py`
- create `tests/unit/test_filesystem.py`
- modify `src/lesson_graph_app/config.py` to add `data_dir: Path` if absent

Failing test (written first):
```python
# tests/unit/test_filesystem.py — full content in subagent output
```

Order:
1. Write failing tests in `tests/unit/test_filesystem.py`.
2. Run; confirm failures.
3. Implement `LocalFilesystem` adapter.
4. Run tests; confirm green.
5. Run full CI locally.

Verification:
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest tests/unit/test_filesystem.py -v
uv run pytest --cov
```

Do not touch:
- `src/lesson_graph/` (schema package — not in scope)
- Any other `tests/unit/` file
- `docs/`, `specs/`, `AGENTS.md`, ADRs

### 5. Execute

Branch, write failing tests, commit:

```bash
git fetch origin && git checkout -B feat/T1-data-directory origin/main
# write tests/unit/test_filesystem.py
uv run pytest tests/unit/test_filesystem.py -v   # confirm red
git add tests/unit/test_filesystem.py
git commit -m "$(cat <<'EOF'
test(T1): failing tests for local filesystem adapter

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

Implement, run pre-flight, commit:

```bash
# implement src/lyw_core/storage/
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest --cov --cov-fail-under=90
git add src/lyw_core/storage/
git commit -m "$(cat <<'EOF'
feat(T1): local filesystem adapter rooted at data_dir

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

### 6. Closeout

Update tracker:
- Tick the T1 box in `docs/plans/phase-1-ingest-tracker.md`.
- Append to "Decisions made":

  > 2026-MM-DD — T1: filesystem adapter creates `data_dir` on first
  > write rather than failing if missing. Rationale: the deployment
  > shape is single-user self-hosted; first-run UX should not require
  > the user to pre-create directories. Surface area for accidental
  > silent creation outside `data_dir` is bounded by the traversal
  > check.

```bash
git add docs/plans/phase-1-ingest-tracker.md
git commit -m "$(cat <<'EOF'
chore(T1): tick T1 complete, add decisions to phase-1-tracker

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

Push and merge:

```bash
git push -u origin feat/T1-data-directory
gh pr create --title "T1: local filesystem adapter rooted at data_dir" \
  --body "Covers spec deliverable: 'Local data directory layout for source PDFs and derived assets.' See \`docs/plans/phase-1/T1-data-directory.md\`."
gh pr merge --squash --delete-branch
git checkout main && git pull --ff-only
```

Then run `/clear` to reset context, scan the tracker for the next `[ ]` entry, and re-invoke run-task for that T-number.

## What good looks like

- Two or three commits on the branch, each a logical unit.
- Test output shown raw at every gate.
- Tracker checkbox ticked, decision recorded with rationale.
- PR description names the spec deliverable.
- Coverage at or above the 90% gate.
- No files touched outside the "Files created or changed" list.
