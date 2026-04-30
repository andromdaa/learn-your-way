# T4 — Timeline Arq integration (extend personalize_concept + generate endpoint)

## ID and one-line summary

T4: Wire `TimelineGenerator` into the `personalize_concept` Arq job and extend `POST /lessons/{id}/generate` to accept `kind="timeline"`.

## Goal

T3 shipped `TimelineGenerator` as a directly-callable library. This task wires it into the existing async generation path, following the same pattern as T2 for mind maps.

The timeline's skip path must be handled correctly: when `TimelineGenerator.generate()` returns `TimelineSkipped`, the Arq job logs a structured event and returns without writing any asset or calling `save_derived_asset`. The job still exits cleanly (no exception) so the polling endpoint returns `status="complete"` with a result payload of `{"skipped": true, "reason": "no_temporal_metadata"}`.

Content-addressed storage for the non-skip path: encode Mermaid string as bytes, call `data_dir.write_asset(content.encode(), suffix=".mmd")`, persist `DerivedAsset` row.

The `GenerateRequest.kind` Literal expands to include `"timeline"`. The `_VALID_KINDS` frozenset expands.

## Files created or modified

- `src/lyw_core/worker/jobs/personalize.py` — **modify**: add `"timeline"` to `_VALID_KINDS`; add `elif kind == "timeline":` branch that instantiates `TimelineGenerator`, checks for `TimelineSkipped`, runs `TimelineValidator` + `run_validators` on the non-skip path, and returns `content`.
- `src/lyw_core/api/routes/generate.py` — **modify**: expand `GenerateRequest.kind` Literal to include `"timeline"`.
- `tests/unit/test_timeline_arq.py` — **create**: unit tests for the `timeline` branch of `personalize_concept`. Test both paths: non-skip path persists the asset; skip path returns `{"skipped": true}` without writing to `data_dir` or `db`. Confirm `ValidationError` from `TimelineValidator` causes the job to raise.
- `tests/unit/test_api_generate.py` — **modify**: add a test that `POST /lessons/{lesson_id}/generate` with `kind="timeline"` returns 202.

## Depends on

T3.

## Acceptance

```
uv run pytest tests/unit/test_timeline_arq.py tests/unit/test_api_generate.py -v
uv run mypy
uv run ruff check .
uv run pytest --cov
```

All pass, coverage >= 93 %. The skip path test confirms no DAO write occurs. The non-blocking property of the generate endpoint is already covered by T2's test.

## Out of scope

- Slide wiring (T6).
- Any change to `WorkerSettings.functions`.
- Populating `temporal_position` in the ingest pipeline.

## Conventions

**Lesson-level `concept_id` sentinel (same as T2):** Timelines are
lesson-level. Use `LESSON_SCOPED_CONCEPT_ID` from `src/lyw_core/db/dao.py`
(`"__lesson__"`) as the `concept_id` when enqueuing a `timeline` job and
when constructing the DAO `DerivedAsset` record. Do not use empty string or
`None`.

**Two `DerivedAsset` types:** Same layering as T2. Construct the Pydantic
`lesson_graph.models.DerivedAsset` from generator output; derive the DAO
`lyw_core.db.dao.DerivedAsset` record from it before calling
`save_derived_asset`. The skip path must not call `save_derived_asset` at all.

## Risk notes

- The `TimelineSkipped` sentinel return type means the Arq job function signature returns `dict[str, str | bool]` or `dict[str, object]` rather than just `dict[str, str]`. The typing must be compatible with Arq's job result serialisation (Arq serialises the result with `msgpack` by default; a plain dict with string and bool values is fine).
- If the skip path is not handled carefully, the job may raise an `AttributeError` when trying to call `.encode()` on a `TimelineSkipped` object. The isinstance check (`if isinstance(result, TimelineSkipped):`) must come before any string handling.
