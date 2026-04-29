# Phase 2 — Personalization and assessment

## Goal

Implement text personalization and assessment on top of the canonical
lesson graph from phase 1. Phase 3 modality generators consume the
output of this phase.

## Deliverables

- [ ] Learner profile data model and `POST /profiles` endpoint.
- [ ] Re-leveling: rewrite text to a target readability that matches
      the learner's grade level. Every change diffable against source.
- [ ] Interest-based example replacement: replace clearly
      "personalizable" examples (analogies, sample problems) with
      examples tied to the learner's stated interests. Never invent
      content not anchored to a `SourceSpan`.
- [ ] Embedded multiple-choice questions tied to learning objectives,
      with rationale and source citation.
- [ ] Section-level quizzes (5–10 items per section) with "Glows" and
      "Grows" feedback.
- [ ] Mnemonic memory aids for high-priority concepts.
- [ ] Quiz signal capture and the gap detector that selects next-step
      concepts to revisit.
- [ ] `POST /attempts` and `POST /recommendations/next` endpoints
      from `docs/04-api.md`.

## Out of scope

- Any modality beyond immersive text — slides, mind maps, and
  timelines belong to phase 3.
- Illustration generation.
- Sequencing models or contextual-bandit personalization. Phase 2 is
  explicit-profile plus quiz feedback only.

## Acceptance criteria

- Personalization output is diffable against source. Every replacement
  is recorded with a span reference and a justification.
- A schema-conforming `personalization_profile` exists and is
  documented.
- Quiz items satisfy all `AssessmentItem` invariants from
  `docs/02-data-model.md`.
- For a smoke-test learner profile, the gap detector recommends a
  concept whose source spans cover the failed quiz item's span.
- Pedagogy rubrics from `docs/02-data-model.md` are encoded as
  validators that gate persistence of personalized text and quiz
  items.

## Implementation notes

- Re-leveling is a constrained generation task. The prompt must
  instruct the model to preserve facts, terminology, and structure;
  only sentence complexity and word choice may change.
- Example replacement is more delicate. Define what counts as a
  "personalizable" segment up front (analogies, illustrative
  scenarios, flavor text) and refuse to rewrite anything else. Mark
  each replacement with explicit metadata.
- Quiz generation prompts must require the model to cite source
  spans. Discard items where the cited span does not actually support
  the question.
- The gap detector in v1 is rule-based: weak items map to their cited
  concepts; the detector returns the highest-priority unmastered
  prerequisite. Sequencing models are out of scope.

## Pedagogy rubrics

Encoded as validators:

- Source faithfulness: no claim in personalized text or quiz item is
  unsupported by a `SourceSpan`.
- Coverage: section quizzes touch every learning objective in the
  section.
- Emphasis: section quizzes weight high-priority objectives more than
  low-priority ones.
- Adaptability: re-leveling actually moves the readability score
  toward the target grade.
- Active learning: each section produces at least one item that
  requires application or analysis, not pure recall.
- Clarity of learning intentions: every quiz item names the objective
  it assesses.
