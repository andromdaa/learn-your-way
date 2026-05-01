# Initiative — CI Integration Coverage

## Goal

A `pytest -m integration` job in `.github/workflows/ci.yml` runs on every PR (or nightly), exercising parse → chunk → ingest → personalize → API-poll end-to-end against Testcontainers-managed Redis and Qdrant and a mock or recorded Ollama. The next chunker false-positive or worker-boundary exception is caught in CI, not by running `scripts/run_pipeline.py` against a real chapter.

## Why now

Every issue in the recurrence table was discovered the same way: a human or automated agent running the full pipeline by hand against `chapter.pdf`. Today's CI (`.github/workflows/ci.yml:13-52`) runs only `ruff`, `mypy`, and `pytest --cov` — no integration job, no real PDF, no Redis/Arq round-trip.

The infrastructure is in place. `tests/integration/` already exists with `test_ingest_job.py`, `test_retrieval_qdrant.py`, and `test_ollama_live.py`. `testcontainers>=4.14.2` is already a dev dep (`pyproject.toml:143`). The wiring is not.

Three specific failures from the audit that a CI integration job would have blocked:

- `ReplaceSourceTooThinError` (#82) — raised inside the worker, fails to deserialize at the API endpoint. A pickle round-trip test using Testcontainers Redis would have caught it before merge.
- `OllamaError` (#83) and custom `ValidationError` (#84) — same pickle-deserializer bomb, same testable shape.
- Chunker over-extraction (123 concepts from one chapter PDF; 10-30 expected) — a concept-count assertion in a smoke test would have flagged it at merge time.

## Scope (in)

- A `pytest -m integration` job in `.github/workflows/ci.yml` that boots Redis and Qdrant via Testcontainers and runs the integration suite.
- A smoke test that ingests a chapter fixture, asserts between 5 and 60 concepts are produced, triggers one `personalize_concept` per kind, and asserts that a forced exception surfaces as `status="failed"` (not a 500).
- A pickle-invariant test asserting every `Exception` subclass under `src/lyw_core/` survives `pickle.loads(pickle.dumps(...))` with all attributes intact.

## Scope (out)

- Real Ollama in CI (use a fake `ModelClient` or recorded responses; live `gemma3:4b` is a separate discussion).
- Coverage gates for integration tests (the 93% gate stays a unit-test gate).
- Re-architecting existing integration tests beyond what is needed to run them in CI.
- The empty-asset write at `src/lyw_core/worker/jobs/personalize.py:181-183` — point-fix filed separately; the smoke test's non-empty asset assertion should catch the regression.

## Sub-PR breakdown

1. **CI job wiring** — Add a `pytest -m integration` job to `.github/workflows/ci.yml` that boots Testcontainers services (Redis, Qdrant) and runs the existing integration suite. Clarify whether `test_ollama_live.py` is CI-runnable or needs a mock substitute before wiring it.
2. **Smoke test + invariant test** — Add an end-to-end fixture test (chapter PDF → 5-60 concepts → at least one `personalize_concept` round-trip with `status="failed"` on a forced exception) and a pickle-invariant test sweeping every `Exception` subclass under `src/lyw_core/`.

## Success criteria

- A PR introducing any of #82/#83/#84 from clean main fails CI before merge.
- Integration job wall-clock under ~6 minutes on the GitHub-hosted runner.
- Smoke test ingests a chapter fixture and yields between 5 and 60 concepts; any count outside that range fails.
- Pickle invariant test passes for every `Exception` subclass under `src/lyw_core/`.

## Rough effort

Small to medium. Job wiring is small (single PR, under 1 week). Meaningful end-to-end fixture and invariant test push it to medium (2 PRs, ~2 weeks total).

## Risks / open questions

- **Blocking gate vs. nightly while flake risk is unknown.** Blocking trades CI flake risk for tight feedback; nightly accepts ~24h of a bug landing without detection. Recommendation: run nightly first, promote to blocking after one clean sprint with no spurious failures.
- `tests/integration/test_ollama_live.py` already exists — clarify before wiring whether it is CI-runnable without a live Ollama instance or needs a recorded-response substitute.
- Real Ollama in CI vs. recorded fake: recorded responses are brittle to prompt drift; live inference is slow and consumes cloud-runner minutes. Decision deferred to the CI-wiring PR.

## ADR impact

None. CI job wiring is infrastructure, not an architecture decision. If a fake Ollama image or new service is added, an ADR may be warranted at that time.

## Cross-initiative dependencies

None — this initiative can start immediately and is the recommended first step. Initiatives 2 and 3 benefit from this landing before they do, but are not blocked on it.
