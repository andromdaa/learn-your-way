# Phase 1 Tracker

Compact index for Phase 1 task work. Detailed task plans live in
`docs/plans/phase-1/`. The source contract remains
`specs/phase-1-ingest.md`.

## Status

Not started. T0a tooling and T0b scaffolding smoke test shipped on
main. Phase 1 task work begins at T0c.

Each T-task is intended to be one branch, one PR, one agent session,
around 400 LoC, no more than six files touched, and no later
T-numbers as prerequisites.

## Tasks

- [x] [T0c: Package skeleton and test directory restructure](phase-1/T0c-package-skeleton.md)
- [x] [T1: Settings, logging, runtime dependency manifest](phase-1/T1-settings-logging.md)
- [x] [T2: Filesystem adapter and data directory layout](phase-1/T2-filesystem-adapter.md)
- [x] [T3: Docker compose for Qdrant and Redis](phase-1/T3-services-healthcheck.md)
- [x] [T4: SQLite schema, migrations, and source/lesson DAO](phase-1/T4-sqlite-dao.md)
- [x] [T5: Docling PDF parser to ParsedDocument](phase-1/T5-docling-parser.md)
- [x] [T6: Round-trip span verifier](phase-1/T6-span-verifier.md)
- [ ] [T7: Heuristic chunker and ConceptNode provenance field](phase-1/T7-heuristic-chunker.md)
- [x] [T8: OllamaModelClient implementing ModelClient](phase-1/T8-ollama-client.md)
- [ ] [T9: LLM-refined chunker](phase-1/T9-llm-refined-chunker.md)
- [x] [T10: BM25 retrieval pipeline and embedding model ADR](phase-1/T10-bm25-retrieval.md)
- [ ] [T11: Qdrant dense retrieval](phase-1/T11-qdrant-retrieval.md)
- [ ] [T12: Cross-encoder reranker and hybrid pipeline](phase-1/T12-hybrid-reranker.md)
- [ ] [T13: Inspection CLI](phase-1/T13-inspection-cli.md)
- [ ] [T14: Arq worker scaffolding and ingest pipeline](phase-1/T14-arq-ingest-worker.md)
- [ ] [T15: FastAPI sources and lessons endpoints](phase-1/T15-fastapi-endpoints.md)

## Decisions Made

- 2026-04-29: T2 uses SHA-256 with a two-char prefix shard for asset paths
  (`assets/<xx>/<full_digest>[.ext]`). Rationale: mirrors git object layout,
  gives deterministic paths, avoids directory fan-out at scale without a
  separate registry. Path traversal protection resolves all paths and checks
  the resolved prefix against `data_dir`, raising `ValueError` on violation.

- 2026-04-29: T0c uses a placeholder `integration`-marked test until real
  integration tests arrive. Rationale: `pytest -m integration` must exit 0
  before any service-backed tests exist, and the placeholder keeps the marker
  path selectable without requiring Qdrant, Redis, or end-to-end fixtures.
- 2026-04-29: T1 pins `gemma3:4b` as `LYW_MODEL_NAME` default and uses
  `str`-typed URLs (not `AnyUrl`). Rationale: `gemma3:4b` is the correct
  Ollama tag for Gemma 4 4B; `AnyUrl` adds round-trip `str()` surprises
  that downstream service clients (httpx, qdrant-client, redis-py) don't
  need. Pre-commit ruff hooks use `language: system` pointing at the
  nix-provided ruff binary to avoid the dynamically-linked venv binary
  failing on NixOS.

- 2026-04-29: T3 adds `pytest-asyncio` (asyncio_mode = "auto") as a dev dependency and `asyncio_mode = "auto"` to pytest config. Rationale: healthcheck probes are async; auto mode avoids per-test `@pytest.mark.asyncio` decoration and is the recommended default for fully-async test suites. Pre-commit mypy hook extended with `httpx`, `redis[hiredis]`, `qdrant-client`, `testcontainers`, and `pytest-asyncio` additional_dependencies so the isolated hook env can resolve all imports.

- 2026-04-29: T3 pins `qdrant/qdrant:v1.14.1` and `redis:7.4.3-alpine` in docker-compose.yml. Rationale: avoids silent breakage from `:latest` drift; both are the current stable tags at time of writing and match the qdrant-client 1.17.1 runtime dependency.

- 2026-04-29: T5 imports `DocItem`, `DoclingDocument`, `DocItemLabel`, `BoundingBox`, `CoordOrigin`, `Size` from their canonical defining submodules (`docling_core.types.doc.document`, `.labels`, `.base`) rather than re-exporting intermediaries. Rationale: `docling_core` has no `__all__` on its intermediate `__init__` modules, causing mypy --strict `attr-defined` errors on re-exported names; direct submodule imports resolve this without ignoring mypy. `doc.num_pages()` (untyped) replaced by `len(doc.pages)` (typed `dict`) for the same reason. Unit tests mock `DocumentConverter.convert` so no ML inference runs; integration test is marked `@pytest.mark.skip` until the OpenStax fixture is present locally.

- 2026-04-29: T5 uses `fpdf2` as the dev dependency for generating the tiny PDF fixture. Rationale: lightweight, pure-Python, no native dependencies — matched the fixture need without pulling in a heavier rendering stack.

- 2026-04-29: T6 places `SpanVerificationFailure` as a frozen `dataclass` (not a Pydantic model). Rationale: it is a diagnostic/error value — no validation or serialization needed, and `frozen=True` gives immutability with zero overhead. `verify_spans` checks inverted spans defensively (even though Pydantic prevents creating them via normal construction) because `model_construct` bypasses validators and downstream code could produce unchecked spans. `hypothesis` added to `[dependency-groups] dev` alongside `pytest-asyncio` (same dev tooling tier).

- 2026-04-29: T4 stores `concepts` and `source_spans` as relational rows (not JSON blobs) in the SQLite schema. Rationale: the spec requires querying by `source_id` and `lesson_id`; relational rows keep those queries cheap and allow `ON DELETE CASCADE` to clean up spans atomically when a lesson is replaced. JSON blobs would require full-graph loads for any span query. Upsert strategy: delete child `concepts` rows (cascading to `source_spans`) then re-insert, giving a clean replace without needing UPSERT conflict resolution on multiple tables. Schema is applied via `executescript` to avoid comment-parsing issues from semicolons inside SQL comments.

- 2026-04-29: T8 injects `httpx.AsyncBaseTransport` into `OllamaModelClient.__init__` for unit-test mocking rather than patching. Rationale: avoids `unittest.mock.patch` fragility (import-path coupling); `httpx.MockTransport` is the library's own test seam and works cleanly with `async with httpx.AsyncClient(transport=...)`. The retry loop only retries on non-`OllamaError` exceptions (i.e., network-level failures), not on HTTP error responses, so a bad model name raises immediately without burning retries.

- 2026-04-29: T10 indexes one Haystack Document per ConceptNode (not per SourceSpan), using the first source_span as the canonical provenance anchor in each RetrievalHit. Rationale: BM25 operates on the concept's own text fields (title + summary + learning_objective) which are the coherent semantic unit; indexing per-span would duplicate documents with the same content and produce noisy ranking. A single canonical span per hit keeps the round-trip verifier test straightforward.

- 2026-04-29: T10 creates InMemoryBM25Retriever inside retrieve() rather than storing it as an instance field. Rationale: Haystack's InMemoryBM25Retriever is a lightweight stateless wrapper around the document store; instantiation cost is negligible and avoids any state-sharing issues if the store is mutated between calls. This matches the documented usage pattern for standalone (non-pipeline) retriever calls.

## Open Questions

_(empty - record blockers and ambiguities here. Resolve to a decision
or escalate to a spec/ADR change.)_

## Out-of-Spec Discoveries

_(empty - record anything found during implementation that conflicts
with or extends `specs/phase-1-ingest.md`. Each entry must end with
either "reconciled in PR #N" or "deferred to phase 2".)_

## Spec Coverage

| `specs/phase-1-ingest.md` deliverable | Covered by |
| --- | --- |
| PDF parser using Docling produces a `ParsedDocument` with page and character offsets. | T5 |
| Chunker emits `ConceptNode` instances with at least one non-empty `SourceSpan`. | T7, T9 |
| Inspection CLI prints concept tree with span anchors, learning objectives, and prerequisites. | T13 |
| Round-trip test: every character in every span resolves back to source text. | T6, exercised in T7, T9, T15 |
| Hybrid retrieval: BM25, dense vectors, and cross-encoder reranker. | T10, T11, T12 |
| SQLite schema for lesson metadata and source registry. | T4 |
| Local data directory layout for source PDFs and derived assets. | T2 |
| `POST /sources` and `GET /lessons/{id}` endpoints functional end-to-end. | T14, T15 |
| `src/lesson_graph/models.py` schema implemented and tested. | Shipped in T0; provenance field in T7 |
| `docker-compose.yml` brings up Qdrant and Redis. | T3 |
| `OllamaModelClient` implementing `ModelClient` protocol. | T8 |

## Architectural Artifacts

| Artifact | Task |
| --- | --- |
| ADR-0006: `lyw_core` sibling package | T0c |
| ADR-0007: embedding model (`all-MiniLM-L6-v2`) | T10 |
| ADR-0008: `ConceptNode.provenance` field | T7 |
| `tests/` reshaped into `unit/`, `integration/`, `fixtures/` | T0c |
| `integration` pytest marker | T0c |
