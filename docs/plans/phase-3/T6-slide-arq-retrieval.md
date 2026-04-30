# T6 — Slide Arq integration + asset retrieval endpoint

## ID and one-line summary

T6: Wire `SlideGenerator` into the `personalize_concept` Arq job, extend `POST /lessons/{id}/generate` to accept `kind="slides"`, and add a `GET /assets/{asset_id}` retrieval endpoint backed by `get_derived_asset`.

## Goal

T5 shipped `SlideGenerator` as a directly-callable library. This task wires it into the async generation path and closes the last spec deliverable: "Asset retrieval by ID via the existing `get_derived_asset` DAO."

The slide generator's output is a `SlideDeck` (list of `Slide` objects). The Arq job serialises the deck to JSON and writes it to content-addressed storage as `data_dir.write_asset(deck_json.encode(), suffix=".json")`. The DAO `DerivedAsset` row is persisted with `kind="slides"`. The returned dict includes `{"asset_id": ..., "file_path": ...}`.

The asset retrieval endpoint is `GET /v1/assets/{asset_id}`. It reads the `derived_assets` table by `id` (not the current `(lesson_id, concept_id, kind, profile_id)` composite key — a new DAO method `get_derived_asset_by_id` is needed). It returns the file content (text/plain for `.txt` and `.mmd` assets, application/json for `.json` assets) or 404 if not found.

The `GenerateRequest.kind` Literal expands to include `"slides"`. The `_VALID_KINDS` frozenset expands.

This task also verifies the end-to-end non-blocking property for slides: the acceptance test asserts the interactive path responds while a slides generation job is in-flight.

## Files created or modified

- `src/lyw_core/worker/jobs/personalize.py` — **modify**: add `"slides"` to `_VALID_KINDS`; add `elif kind == "slides":` branch that instantiates `SlideGenerator`, awaits `.generate()`, serialises the resulting `SlideDeck` to JSON, and returns the content string.
- `src/lyw_core/api/routes/generate.py` — **modify**: expand `GenerateRequest.kind` Literal to include `"slides"`.
- `src/lyw_core/db/dao.py` — **modify**: add `get_derived_asset_by_id(asset_id: str) -> DerivedAsset | None` method to `Database`.
- `src/lyw_core/api/routes/assets.py` — **create**: `GET /v1/assets/{asset_id}` endpoint. Reads the `DerivedAsset` row, reads the file from `data_dir`, returns the file content with appropriate content-type. Returns 404 if asset not found or file missing.
- `src/lyw_core/api/app.py` — **modify**: include the `assets_router` from `routes/assets.py`.
- `tests/unit/test_slide_arq.py` — **create**: unit tests for the `slides` branch of `personalize_concept`. Mock `SlideGenerator.generate` to return a two-slide `SlideDeck`. Confirm the JSON is written to `data_dir` and the DAO `save_derived_asset` is called. Confirm `ValidationError` from `SlideGenerator` causes the job to raise.
- `tests/unit/test_api_assets.py` — **create** (or modify `test_api_generate.py`): test `GET /v1/assets/{asset_id}` returns file content for an existing asset; returns 404 for an unknown id.

## Depends on

T5.

## Acceptance

```
uv run pytest tests/unit/test_slide_arq.py tests/unit/test_api_assets.py tests/unit/test_api_generate.py -v
uv run mypy
uv run ruff check .
uv run pytest --cov
```

All pass, coverage >= 93 %. `GET /v1/assets/{asset_id}` returns file content for a known asset id. `POST /lessons/{id}/generate` with `kind="slides"` returns 202. A concurrent interactive-path request responds without waiting for the slides job.

The spec deliverable "Asset retrieval by ID via the existing `get_derived_asset` DAO" is satisfied by `get_derived_asset_by_id` plus the retrieval endpoint.

## Out of scope

- Frontend rendering of slides.
- Websocket or SSE push notifications (explicitly noted in phase-2 retrospective as a potential phase-3 addition; the spec does not mandate it).
- Deleting or replacing derived assets.
- Streaming generation.

## Risk notes

- Six files is the task budget maximum. This task touches exactly six: `personalize.py`, `generate.py`, `dao.py`, `assets.py`, `app.py`, plus one test file. The test files can be consolidated to `test_slide_arq_and_assets.py` if the budget is tight.
- `get_derived_asset_by_id` is a new DAO method. The existing `get_derived_asset` uses a composite key `(lesson_id, concept_id, kind, profile_id)`; the new method queries by `id` (primary key). This is a straightforward addition with no schema change.
- The asset retrieval endpoint reads file content from `data_dir`. It must handle the case where the DAO row exists but the file has been deleted (return 404, not 500). The `DataDir` class from T2 (phase 1) must be consulted to confirm how to read back a file by path.
- If `SlideDeck` contains `Slide` objects (dataclasses), JSON serialisation requires `dataclasses.asdict()` rather than Pydantic's `.model_dump()`, following the `GlowsGrows` precedent from the phase-2 retrospective.
