# T3 — Timeline generator + validator (Mermaid, temporal skip path, raises on failure)

## ID and one-line summary

T3: Implement `TimelineGenerator` and `TimelineValidator` as a directly-callable library pair; includes the skip path when no concept has `temporal_position` set.

## Goal

The spec requires a timeline generator for chronologically structured content. It produces Mermaid `timeline` diagram source from the lesson graph's `ConceptNode` instances that have a non-`None` `temporal_position`. If no concept in the graph has `temporal_position` set, the generator returns a sentinel indicating the lesson has no temporal structure, and the Arq job (T4) will skip persistence for that case.

The generator sorts concepts by `temporal_position` (ascending) and emits a Mermaid timeline block. It does not call the language model; the structure is deterministic from the lesson graph metadata added in T0c-r2.

The `TimelineValidator` implements `Validator[str]`. It checks:
- The output starts with `timeline` (valid Mermaid timeline preamble).
- At least one event section is present.
- No section title is empty.

Because a timeline is a single result with no fallback, the job layer calls `run_validators` (collect-all, raises `ValidationError`). The generator does not call `save_derived_asset`.

The skip path: if `all(c.temporal_position is None for c in lesson_graph.concepts)`, the generator returns a typed sentinel (`TimelineSkipped`) rather than a Mermaid string. The caller (T4's Arq branch) checks for this sentinel and short-circuits without writing any asset.

## Files created or modified

- `src/lyw_core/modalities/timeline.py` — **create**: `TimelineGenerator` class, `TimelineResult` dataclass (holds the Mermaid string and the list of `concept_id` strings included), and `TimelineSkipped` sentinel dataclass. Generator accepts `(lesson_graph, profile)` and returns `TimelineResult | TimelineSkipped`.
- `src/lyw_core/validators/timeline.py` — **create**: `TimelineValidator` implementing `Validator[str]`.
- `tests/unit/test_timeline_generator.py` — **create**: unit tests covering: a graph with `temporal_position` values produces valid Mermaid in ascending order; a graph with no `temporal_position` values returns `TimelineSkipped`; a graph where only some concepts have `temporal_position` includes only the positioned ones; snapshot test of output shape.
- `tests/unit/test_validators_timeline.py` — **create**: unit tests for `TimelineValidator`. Covers: valid timeline passes, empty string fails, single-section diagram passes, missing preamble fails.

## Depends on

T0c-r2 (requires `ConceptNode.temporal_position` to exist).

## Acceptance

```
uv run pytest tests/unit/test_timeline_generator.py tests/unit/test_validators_timeline.py -v
uv run mypy
uv run ruff check .
uv run pytest --cov
```

All pass, coverage >= 93 %. `TimelineGenerator` returns `TimelineSkipped` for a graph with no temporal metadata. `TimelineValidator` rejects output missing the `timeline` preamble.

## Out of scope

- Arq job wiring (T4).
- API endpoint changes (T4).
- Populating `temporal_position` in the chunker or LLM refiner (out of scope for phase 3; the generator works with whatever is present).
- Language model calls (generation is deterministic from graph metadata).
- Illustration or image output.

## Risk notes

- Mermaid's `timeline` diagram type requires a specific section/event syntax. The generator must produce `section <year or label>` followed by `    <event text>` lines. The validator checks the preamble and at least one section, but the agent should verify current Mermaid timeline syntax in the implementation.
- `temporal_position` is an integer representing ordering, not a year or date. The generator labels sections by position index or by concept title; it must not fabricate date strings that are not in the source. This is a source-fidelity constraint.
