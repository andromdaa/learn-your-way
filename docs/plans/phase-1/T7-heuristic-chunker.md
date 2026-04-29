# T7 - Heuristic Chunker and ConceptNode Provenance Field

## Status

- [ ] T7: Heuristic chunker and `ConceptNode` provenance field

## Goal

Create deterministic first-pass chunking from `ParsedDocument` into
`ConceptNode`s using heading detection and length thresholds. Add a
`provenance` field to `ConceptNode` with `SCHEMA_CHANGE=1` so each
node records whether it came from the heuristic or the LLM refiner.

## Files

- Create `src/lyw_core/chunker/__init__.py`.
- Create `src/lyw_core/chunker/heuristic.py`.
- Create `tests/unit/test_chunker_heuristic.py` with syrupy snapshots.
- Create `docs/adr/0008-concept-node-provenance.md`.
- Modify `src/lesson_graph/models.py` with `SCHEMA_CHANGE=1` to add
  `provenance: Literal["heuristic", "llm_refined"] = "heuristic"`.
- Modify `tests/unit/test_lesson_graph.py`.
- Modify `pyproject.toml` to add `syrupy` to `dev`.

## Depends On

- T5.
- T6.

## Acceptance

- `uv run pytest tests/unit/test_chunker_heuristic.py tests/unit/test_lesson_graph.py`
  passes.
- The snapshot is stable.
- The round-trip verifier returns no failures on the tiny fixture.
- `uv run mypy` is strict-clean.

## Out of Scope

- Model-driven concept naming or prerequisites.
- Personalization.
- Mutation of source spans.
- Pedagogy refinement beyond placeholder heading-stamped fields.

## Risk Notes

- Confirm `ConceptNode.learning_objective` accepts the heading-stamped
  value before the schema edit.
- ADR-0008 should explain why provenance lives on the node.
