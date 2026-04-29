# T9 - LLM-Refined Chunker

## Status

- [ ] T9: LLM-refined chunker

## Goal

Refine heuristic chunks by passing each through a `ModelClient` prompt
that produces a validated `title`, `summary`, `learning_objective`,
and `prerequisites`. The model output must validate against the
pydantic schema before persistence, and refined nodes set
`provenance` to `"llm_refined"`.

## Files

- Create `src/lyw_core/chunker/llm_refiner.py`.
- Create `src/lyw_core/chunker/prompts/concept_extraction.txt`, or a
  typed `.py` prompt template.
- Create `tests/unit/test_chunker_llm.py`.
- Use a stub `ModelClient` returning canned JSON.
- Cover well-formed payloads, malformed payloads, and unchanged spans.

## Depends On

- T7 for heuristic chunks.
- T8 for the `ModelClient` implementation.

## Acceptance

- Stub-client tests pass.
- Malformed payloads fail with a typed error, not a silent fallback or
  bare `Exception`.
- `mypy` is strict-clean.
- `provenance == "llm_refined"` on all refined nodes.

## Out of Scope

- Personalization.
- Example replacement or re-leveling.
- Any mutation of source spans.
- Prompt quality tuning beyond what makes tests pass.

## Risk Notes

- Prompt iteration is open-ended; time-box it.
- Long chunk text can exceed model context. Truncate with a documented
  sentinel and record the threshold in the index decisions.
