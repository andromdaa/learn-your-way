# T5 — Slide generator + validator (per-slide discard, MCQGenerator pattern)

## ID and one-line summary

T5: Implement `SlideGenerator` and `SlideValidator` as a directly-callable library pair; uses the MCQGenerator discard pattern (iterate validators manually, discard failing slides).

## Goal

The spec requires a slide generator producing structured slide decks with speaker notes and source spans on every slide. Unlike the mind-map and timeline generators, the slide generator may discard individual failing slides rather than aborting on first failure — matching the `MCQGenerator` pattern from ADR-0011.

The generator uses a two-step approach mandated by the spec:
1. **Outline step**: call the language model to produce an outline (slide titles, key points per slide, source spans). The outline is a structured JSON object validated by Pydantic.
2. **Flesh-out step**: for each slide in the outline, call the language model to produce the full slide body and speaker notes.

A `Slide` dataclass holds: `title: str`, `body: str`, `speaker_notes: str`, `source_spans: list[SourceSpan]`, `concept_id: str`. A `SlideDeck` dataclass holds: `slides: list[Slide]`, `based_on_concepts: list[str]`.

The `SlideValidator` implements `Validator[Slide]`. It checks:
- `title` is non-empty.
- `body` is non-empty.
- `source_spans` is non-empty (source fidelity invariant).
- `concept_id` is non-empty and resolves to a concept in the lesson graph.

The generator iterates validators manually on each `Slide` (not `run_validators`) and discards slides that fail, logging a structlog warning per discarded slide. If all slides are discarded, the generator raises `ValidationError` (cannot persist an empty deck).

The generator accepts `(lesson_graph, profile, model_client)`. It is async because it calls the language model. No persistence; that belongs in T6.

## Files created or modified

- `src/lyw_core/modalities/slides.py` — **create**: `Slide` dataclass, `SlideDeck` dataclass, `SlideOutlineItem` Pydantic model (for JSON parsing of the outline step), `SlideGenerator` class.
- `src/lyw_core/modalities/prompts/__init__.py` — **create** (or extend if mindmap prompts exist): prompt builders. For this task: `build_slide_outline_messages(lesson_graph, profile)` and `build_slide_body_messages(outline_item, concept)`.
- `src/lyw_core/validators/slides.py` — **create**: `SlideValidator` implementing `Validator[Slide]`.
- `tests/unit/test_slide_generator.py` — **create**: unit tests with mocked `ModelClient`. Tests cover: a two-concept lesson produces a deck with at least one slide; a slide with no `source_spans` from the model is discarded; all slides failing raises `ValidationError`; snapshot test of output shape (titles, notes structure). Use `side_effect` list on mock for the outline then per-slide calls.
- `tests/unit/test_validators_slides.py` — **create**: unit tests for `SlideValidator`. Covers: valid slide passes, empty title fails, empty source_spans fails, empty concept_id fails.

## Depends on

T0c-r1, T0c-r2.

## Acceptance

```
uv run pytest tests/unit/test_slide_generator.py tests/unit/test_validators_slides.py -v
uv run mypy
uv run ruff check .
uv run pytest --cov
```

All pass, coverage >= 93 %. The "all slides discarded" case raises `ValidationError` (not a silent empty list). The discarded-slide case logs a warning and continues. Snapshot test captures the output structure.

## Out of scope

- Arq job wiring (T6).
- API endpoint changes (T6).
- Slide narration or TTS (spec out of scope).
- Illustration generation (spec out of scope).
- HTML/PDF rendering of the deck (out of scope for phase 3).

## Risk notes

- The two-step LLM call is the primary prompt-iteration risk. The outline step produces JSON that the generator parses with Pydantic. If the model produces malformed JSON, the generator must catch `json.JSONDecodeError` and `pydantic.ValidationError` and raise a typed error (following T9's `LLMRefinerError` pattern). The prompt must be explicit about the required JSON schema.
- Each slide requires at least one `SourceSpan`. The model must cite spans in its outline response. If the model omits spans, the `SlideValidator` discards the slide. The prompt must explicitly require span citation and the mock tests must cover the discard path.
- The two-step approach means each `SlideGenerator.generate()` call makes `1 + N` model calls (one outline + one per slide). For a lesson with 10 concepts and 3 slides per concept, this is 31 calls. The Arq job timeout must accommodate this. The agent should note this in the PR but does not need to set a custom timeout in phase 3.
- Prompt builders go under `src/lyw_core/modalities/prompts/` to parallel the `src/lyw_core/assessment/prompts/` structure. If the `modalities/` package does not exist before T5, the agent must create the `__init__.py` (already done in T1).
