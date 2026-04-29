# T14 - Arq Worker Scaffolding and Ingest Pipeline

## Status

- [ ] T14: Arq worker scaffolding and ingest pipeline

## Goal

Stand up the Arq worker from ADR-0003 and the single ingest job:
parse, chunk, persist, build BM25 index, and build Qdrant index.
Keeping worker entry point and job semantics out of the API diff
reduces blast radius for later API work.

## Files

- Create `src/lyw_core/worker/__init__.py`.
- Create `src/lyw_core/worker/settings.py` with Arq `WorkerSettings`.
- Create `src/lyw_core/worker/jobs/ingest.py`.
- Create `tests/unit/test_ingest_job_unit.py`.
- Stub DAO and retrieval in the unit test.
- Create `tests/integration/test_ingest_job.py`.
- Modify `pyproject.toml` to add `arq`.

## Depends On

- T2 for filesystem adapter.
- T3 for Qdrant and Redis services.
- T4 for DAO.
- T9 for refined chunking, or T7 for the heuristic-only smoke path.
- T10 for BM25.

## Acceptance

- `uv run pytest tests/unit/test_ingest_job_unit.py` passes without
  Docker.
- `uv run pytest -m integration tests/integration/test_ingest_job.py`
  passes with Docker.
- The tiny fixture produces a persisted lesson and populated BM25
  index.
- `uv run arq lyw_core.worker.settings.WorkerSettings` boots cleanly.

## Out of Scope

- Generation jobs.
- Dead-letter queue.
- Retry policies beyond Arq defaults.

## Risk Notes

- None recorded.
