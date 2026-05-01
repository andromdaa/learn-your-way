**Status: Superseded by [ADR-0016](0016-phase-2-3-scope-reduction.md) (2026-05-01).**

# ADR-0010 — AssessmentItem.concept_id

## Status

Accepted (2026-04-30)

## Context

The gap detector (T12) must map a failed quiz item to its parent concept
without a join or secondary lookup. Phase 1 left `AssessmentItem` without
a direct reference to the concept it assesses; the only relationship was
implicit through shared `SourceSpan` ranges.

The clarity of learning intentions rubric (T4) also requires each item to
name the objective it assesses, which is only resolvable through a concept
reference.

## Decision

Add `concept_id: str` to `AssessmentItem`, enforced non-empty by a
`@field_validator`. The field stores the `ConceptNode.id` of the concept
the item assesses.

Runtime validation that `concept_id` resolves to a known concept in a
specific lesson graph is the clarity validator's responsibility (T4),
not a model invariant.

## Consequences

- The gap detector can look up the parent concept directly from a failed
  item without joining through `source_spans`.
- The clarity validator can resolve `concept_id` → `ConceptNode.learning_objective`
  to verify the item names the correct objective.
- All `AssessmentItem` construction sites (generators, tests) must supply
  a non-empty `concept_id`. Generators that do not supply one will fail
  at construction time.
- No SQL schema change is introduced here; T8 adds the `assessment_items`
  table and will include a `concept_id TEXT NOT NULL` column.

## Alternatives considered

**Derive from source_spans at query time**: Requires a join through the
`source_spans` table at every gap-detector query. Rejected because the
gap detector is called on every quiz submission and the direct field is
O(1) vs. O(N) join.

**Foreign-key relationship in a join table**: Adds schema complexity for
a one-to-one relationship. Rejected in favour of the simpler denormalised
field on the model.
