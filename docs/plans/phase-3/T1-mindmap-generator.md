# T1 — Mind-map generator + validator (Mermaid, single-output, raises on failure)

## ID and one-line summary

T1: Implement `MindMapGenerator` and `MindMapValidator` as a directly-callable library pair; no Arq wiring yet.

## Goal

The spec requires a mind-map generator that produces Mermaid flowchart source from the concept graph, paired with a modality-specific validator. This task ships the generator and validator as pure library code — no worker integration, no API changes. Keeping generator and validator separate from Arq wiring (T2) respects the spec's sequencing rule ("library-first, integration second") and keeps the diff within the 400-line budget.

The generator takes a `LessonGraph` and a `PersonalizationProfile`, prunes the concept graph to a per-diagram concept budget (12–20 nodes, configurable), and emits Mermaid flowchart source. Pruning is by prerequisite distance from a focal concept (the concept with the most prerequisites, or the first concept if there is a tie). The output is a string of valid Mermaid syntax; no rendering is performed.

The `MindMapValidator` implements the `Validator[str]` Protocol. It checks:
- The output starts with `flowchart` or `graph` (valid Mermaid preamble).
- At least two nodes are present (a one-node diagram has no meaningful structure).
- No node label is empty.

Because a mind map is a single result with no fallback, the job layer calls `run_validators` (collect-all, raises `ValidationError`). The generator itself does not call `save_derived_asset`; persistence is the Arq job's responsibility (T2).

## Files created or modified

- `src/lyw_core/modalities/__init__.py` — **create**: empty package marker.
- `src/lyw_core/modalities/mindmap.py` — **create**: `MindMapGenerator` class and `MindMapPayload` dataclass. Generator accepts `(lesson_graph, profile, focal_concept_id=None, max_nodes=20)` and returns a Mermaid string. Uses a simple BFS/DFS from the focal concept over `ConceptNode.prerequisites` edges, capped at `max_nodes`.
- `src/lyw_core/validators/mindmap.py` — **create**: `MindMapValidator` implementing `Validator[str]`.
- `tests/unit/test_mindmap_generator.py` — **create**: unit tests for `MindMapGenerator` (mocked `ModelClient` if the generator uses it; otherwise pure logic). Tests cover: basic graph with 3 concepts produces valid Mermaid, pruning respects `max_nodes`, focal concept override works, snapshot test of output shape.
- `tests/unit/test_validators_mindmap.py` — **create**: unit tests for `MindMapValidator`. Covers: valid Mermaid passes, empty string fails, single-node diagram fails, missing preamble fails.

## Depends on

T0c-r1, T0c-r2.

## Acceptance

```
uv run pytest tests/unit/test_mindmap_generator.py tests/unit/test_validators_mindmap.py -v
uv run mypy
uv run ruff check .
uv run pytest --cov
```

All pass. Coverage stays >= 93 %. `MindMapGenerator` and `MindMapValidator` are importable from `lyw_core.modalities.mindmap` and `lyw_core.validators.mindmap` respectively.

## Out of scope

- Arq job wiring (T2).
- API endpoint changes (T2).
- Using a language model for the Mermaid generation. Mermaid is deterministic from the lesson graph; no model call is needed. The generator is pure graph-to-text conversion.
- Rendering the Mermaid output (Cytoscape.js rendering is a frontend concern).
- Illustration or image output of any kind.

## Risk notes

- Mermaid node IDs must be valid identifiers (no spaces, special chars). The generator should derive node IDs from `ConceptNode.id` (already a hash-like string) rather than `ConceptNode.title`.
- If `max_nodes` pruning uses BFS from focal concept, prerequisite cycles (allowed by `ConceptNode.prerequisites` being a plain list) would cause an infinite loop. The generator must track visited nodes.
- No model call means no mock needed for the core generator test, keeping tests fast and model-free per AGENTS.md.
