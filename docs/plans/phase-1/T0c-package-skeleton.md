# T0c - Package Skeleton and Test Directory Restructure

## Status

- [ ] T0c: Package skeleton and test directory restructure

## Goal

Establish the two-package layout that every later task builds into:
`lesson_graph` for the canonical schema and `lyw_core` for
application code. Reshape the test tree into `unit/`, `integration/`,
and `fixtures/` so later feature work does not also have to re-home
existing files.

## Files

- Generate `docs/adr/0006-lyw-core-package.md` content.
- Modify `pyproject.toml` to add the `integration` marker under
  `[tool.pytest.ini_options]`.

## Depends On

- None. T0a and T0b are already on main.

## Acceptance

- `pytest tests/unit/` passes with the same tests in new paths.
- `mypy` sees both packages.
- `pytest -m integration` exits 0 with no tests collected.
- `docs/adr/0006-lyw-core-package.md` is committed.

## Out of Scope

- Application code.
- Settings and storage.
- CI changes beyond the marker addition.

## Risk Notes

- None recorded.
