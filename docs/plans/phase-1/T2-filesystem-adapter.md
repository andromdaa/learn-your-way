# T2 - Filesystem Adapter and Data Directory Layout

## Status

- [ ] T2: Filesystem adapter and data directory layout

## Goal

Define the on-disk layout for source PDFs and derived assets under the
configured data directory, per ADR-0004. Provide a thin async
filesystem adapter so ingest, retrieval, and API code share one path
contract.

## Files

- Create `src/lyw_core/storage/__init__.py`.
- Create `src/lyw_core/storage/fs.py` with path helpers and
  content-hashed asset writes.
- Use this layout: `sources/`, `lessons/`, `assets/`, `indexes/`.
- Create `tests/unit/test_storage.py`.
- Create `docs/05-data-layout.md`.

## Depends On

- T1, because it reads `lyw_core.settings.Settings.data_dir`.

## Acceptance

- `pytest tests/unit/test_storage.py` passes.
- Directory bootstrap is idempotent.
- A written PDF round-trips byte-for-byte.
- Content-hashed asset paths are deterministic.
- Attempts to escape `data_dir` raise.

## Out of Scope

- SQLite registry rows.
- Docling parsing.
- Asset generation.
- Anything beyond pure I/O.

## Risk Notes

- Path traversal is the main foot-gun. Resolve paths and assert they
  stay under `data_dir`.
