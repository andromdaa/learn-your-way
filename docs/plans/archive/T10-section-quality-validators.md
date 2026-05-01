# T10 — Coverage, Emphasis, Active Learning Section-Quality Validators

## Status

- [ ] T10: Section-quality validators

## Goal

Implement three section-level validators, all implementing
`Validator[SectionQuizPayload]`:

1. **Coverage**: every `ConceptNode` in the section has at least one
   `AssessmentItem` referencing it via `concept_id`.
2. **Emphasis**: concepts with ≥ 2 prerequisites receive at least as
   many items as concepts with 0 prerequisites. Fails if a
   high-prerequisite concept has 0 items while a zero-prerequisite
   concept has ≥ 2.
3. **Active learning**: at least one item per section has `bloom_level`
   in `{"apply", "analyze", "evaluate", "create"}`. This is precise
   because T0c-r3 added `bloom_level` to `AssessmentItem` and T8's MCQ
   prompt sets it.

## Files

- Create `src/lyw_core/validators/section_quality.py`.
- Create `tests/unit/test_validators_section.py`.

## Depends On

- T3 (validator framework).
- T9 (section quiz generator; T9 → T8 → T0c-r3 is transitive, so
  `bloom_level` is guaranteed available; no additional direct dep
  needed).
- T0c-r2 (`AssessmentItem.concept_id` for coverage check; also
  transitive through T9 → T8, but listed explicitly for clarity).

## Acceptance

- `SectionQuizPayload` dataclass: `concepts: list[ConceptNode]`,
  `items: list[AssessmentItem]`.
- `CoverageValidator.validate(payload)` fails if any concept has no
  item with a matching `concept_id`.
- `EmphasisValidator.validate(payload)` fails if any concept with
  `len(prerequisites) >= 2` has 0 items while any concept with
  `len(prerequisites) == 0` has ≥ 2 items.
- `ActiveLearningValidator.validate(payload)` fails if no item has
  `bloom_level in {"apply","analyze","evaluate","create"}`.
- Tests: pass + fail for each validator with minimal fixtures.
- `ruff check`, `mypy`, `pytest` all pass.

## Out of Scope

- Source faithfulness and clarity validators (T4).
- Adaptability validator (T6).

## Risk Notes

- Items with `bloom_level = None` (generated before T8 fully wired or
  from non-MCQ paths) must be treated as `"remember"` (most
  conservative) so the active learning validator does not silently pass
  on untagged quizzes. Document this handling in the validator's
  docstring.
