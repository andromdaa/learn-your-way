# T2 — Mind-map Arq integration (extend personalize_concept + generate endpoint)

## ID and one-line summary

T2: Wire `MindMapGenerator` into the `personalize_concept` Arq job and extend `POST /lessons/{id}/generate` to accept `kind="mind_map"`.

## Goal

T1 shipped `MindMapGenerator` as a directly-callable library. This task wires it into the existing async generation path: the `personalize_concept` Arq job (which already handles `relevel`, `replace`, `mnemonic`) and the `POST /lessons/{id}/generate` endpoint (which already enqueues jobs and validates `kind`).

The key constraint from the spec: "Asynchronous generation does not block interactive paths." This task's acceptance test must assert that `POST /lessons/{lesson_id}/generate` responds while a generation job is in-flight.

Content-addressed storage follows ADR-0013: `MindMapGenerator` returns a Mermaid string; the Arq job encodes it as bytes and calls `data_dir.write_asset(content.encode(), suffix=".mmd")`, then persists a `DerivedAsset` row via `db.save_derived_asset`.

The `GenerateRequest.kind` Literal in `generate.py` expands from `Literal["relevel", "replace", "mnemonic"]` to include `"mind_map"`. The `_VALID_KINDS` frozenset in `personalize.py` also expands.

## Files created or modified

- `src/lyw_core/worker/jobs/personalize.py` — **modify**: add `"mind_map"` to `_VALID_KINDS`; add an `elif kind == "mind_map":` branch that instantiates `MindMapGenerator`, runs the generator, validates via `MindMapValidator` + `run_validators`, and returns the Mermaid string as `content`.
- `src/lyw_core/api/routes/generate.py` — **modify**: expand `GenerateRequest.kind` Literal to include `"mind_map"`.
- `tests/unit/test_mindmap_arq.py` — **create**: unit tests for the new `mind_map` branch of `personalize_concept`. Mock `db`, `data_dir`, and `MindMapGenerator.generate` (synchronous fixture output). Confirm the asset is written and the DAO `save_derived_asset` is called. Confirm a `ValidationError` from the validator causes the job to raise (not silently swallow).
- `tests/unit/test_api_generate.py` — **modify**: add a test that `POST /lessons/{lesson_id}/generate` with `kind="mind_map"` returns 202 and a `job_id`, while a concurrent `GET /v1/attempts` (or another interactive route) responds without waiting for the job to complete. Use `pytest-asyncio` with a mocked Arq queue.

## Depends on

T1.

## Acceptance

```
uv run pytest tests/unit/test_mindmap_arq.py tests/unit/test_api_generate.py -v
uv run mypy
uv run ruff check .
uv run pytest --cov
```

All pass, coverage >= 93 %. The non-blocking acceptance test (concurrent interactive path responds while job is in-flight) must be present and passing.

## Out of scope

- Timeline or slides wiring (T4, T6).
- Any change to the polling endpoint `GET /lessons/{id}/generate/{job_id}`.
- Any change to `WorkerSettings.functions` — `personalize_concept` is already registered.
- Frontend or Cytoscape.js integration.

## Conventions

**Lesson-level `concept_id` sentinel (decision made):** Mind maps are
lesson-level (they aggregate all or a pruned subset of concepts), not
single-concept. The `derived_assets` table requires `concept_id TEXT NOT NULL`.
Use the constant `LESSON_SCOPED_CONCEPT_ID = "__lesson__"` defined in
`src/lyw_core/db/dao.py` as the `concept_id` value for all lesson-level
generator kinds. The API layer must pass this sentinel when enqueuing a
`mind_map` job. T4 (timelines) uses the same constant.

**Two `DerivedAsset` types:** `lesson_graph.models.DerivedAsset` (Pydantic)
is the generator-output domain model — it has `based_on_concepts` and a rich
`personalization_profile`. `lyw_core.db.dao.DerivedAsset` (plain dataclass)
is the persistence record — it has scalar `concept_id`, `profile_id`,
`file_path`. This task's Arq branch constructs the Pydantic model from
generator output, then derives the DAO record from it before calling
`save_derived_asset`. Do not conflate the two.

## Risk notes

- The `INSERT OR IGNORE` in `save_derived_asset` is keyed on `id` (UUID). The content-addressed file path will differ per run (because UUID is fresh each time), so re-running a generation job for the same `(lesson_id, concept_id, kind, profile_id)` will produce a new row rather than deduplicating. This matches the existing phase-2 behaviour and is acceptable.
