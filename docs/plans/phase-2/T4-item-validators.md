# T4 — Source Faithfulness + Clarity of Learning Intentions Validators

## Status

- [ ] T4: Source faithfulness + clarity validators

## Goal

Implement the two item-level validators that every generator must pass
before its output is returned to the caller.

**Source faithfulness**: given an `AssessmentItem` and a `LessonGraph`,
confirms that every span cited in `item.source_spans` falls within the
character-offset range of at least one `SourceSpan` in the parent
concept's `source_spans`. Rejects items that cite spans outside the
concept's range.

**Clarity of learning intentions**: given an `AssessmentItem` and a
`LessonGraph`, confirms that `item.concept_id` resolves to a
`ConceptNode.id` in the graph and that the node has a non-empty
`learning_objective`.

Both implement `Validator[ItemValidationPayload]` from T3.

## Files

- Create `src/lyw_core/validators/faithfulness.py`.
- Create `src/lyw_core/validators/clarity.py`.
- Create `tests/unit/test_validators_item.py`.

## Depends On

- T3 (validator framework).
- T0c-r2 (`AssessmentItem.concept_id` must exist for clarity validator).

## Acceptance

- `ItemValidationPayload` is a dataclass: `item: AssessmentItem`,
  `lesson_graph: LessonGraph`.
- `SourceFaithfulnessValidator.validate(payload)` returns
  `passed=False, evidence=[offending spans]` when any item span lies
  outside all of the concept's span ranges; `passed=True` otherwise.
- `ClarityValidator.validate(payload)` returns `passed=False` when
  `concept_id` does not match any `ConceptNode.id` in the lesson graph
  or the matching node has an empty `learning_objective`.
- Tests: faithfulness fails on item with span outside concept range;
  faithfulness passes on valid item; clarity fails on unknown
  `concept_id`; clarity passes on valid item.
- `ruff check`, `mypy`, `pytest` all pass.

## Out of Scope

- Coverage, emphasis, active learning validators (T10).
- Adaptability validator (T6).

## Risk Notes

- Span-containment check: an item span is "within" a concept span if
  `doc_id` matches, pages overlap, and the character range is
  contained. The check must handle multi-span concepts (any one
  concept span can satisfy containment). Implement as a module-level
  helper `span_is_contained(item_span, concept_spans)` — it will be
  reused by T8's MCQ generator.
