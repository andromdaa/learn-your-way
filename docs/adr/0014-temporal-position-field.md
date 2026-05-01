**Status: Superseded by [ADR-0016](0016-phase-2-3-scope-reduction.md) (2026-05-01).**

# ADR-0014 — Add `temporal_position` to `ConceptNode`

**Status:** Accepted
**Date:** 2026-04-30
**Deciders:** Cole (project owner), Claude Sonnet 4.6 (agent)

## Context

The phase-3 timeline generator needs to identify concepts that have a
meaningful chronological order and determine how to sequence them in a
Mermaid timeline diagram. Without a field on `ConceptNode` that captures
temporal ordering, the generator has no signal to work from and cannot
distinguish chronologically structured lessons from unordered ones.

Two use-cases drive the requirement:

1. **Skip detection.** If a lesson graph contains no concepts with a
   non-null temporal position, the timeline generator should skip
   generation rather than produce a meaningless diagram.
2. **Ordering.** When temporal positions are present, the generator sorts
   concepts by ascending `temporal_position` to produce a meaningful
   left-to-right or top-to-bottom timeline.

## Decision

Add `temporal_position: int | None = None` to `ConceptNode` in
`src/lesson_graph/models.py`.

- **Type is `int`**, not `float` or `str`. Integer ranks are sufficient
  for all known use-cases (historical periods, curriculum sequencing,
  numbered steps). Floats would allow insertion between existing ranks
  without renumbering, but no insertion use-case exists in phase 3.
  Strings would need a separate sort key; rejected as unnecessary
  complexity.
- **`None` is the default.** All existing serialised lesson graphs
  remain valid without migration. Ingest paths (heuristic and
  LLM-refined chunkers) do not populate `temporal_position` in phase 3;
  the field is populated only when the source has explicit temporal
  structure (a later phase's concern, or manual annotation).
- **Negative values are valid.** BC dates and relative pre-epoch ranks
  require values below zero. Clamping to non-negative would make the
  field useless for history lessons.
- **No SQLite column added in this task.** The DAO stores concepts but
  does not currently need to query by `temporal_position`. The timeline
  generator reads the in-memory graph. If a later task needs
  `WHERE temporal_position IS NOT NULL` queries at the DAO level, that
  task should add the column then with an appropriate migration.

## Alternatives considered

### `temporal_position: float | None`

Floats allow fractional insertion between existing ranks without
renumbering (e.g., insert rank 2.5 between 2 and 3). No such use-case
exists in phase 3, and floats complicate equality comparisons in tests
and serialisation. Rejected.

### `temporal_position: str | None`

A string rank (e.g., `"1500s"`, `"early"`) would be human-readable but
requires a separate sort-key field or a natural-language ordering
heuristic. Rejected as unnecessary complexity; structured integer ranks
are sufficient.

### A separate `TemporalMetadata` sub-model

A sub-model could carry additional fields (era label, calendar system,
precision). Over-engineered for phase 3. A plain `int | None` field is
the minimal viable addition. If richer temporal metadata is needed in a
future phase, the field can be replaced with a sub-model at that point
(a schema change with its own ADR).

### A `chronological: bool` flag without a rank

A boolean would cover skip detection but not ordering. Two fields would
be needed. Rejected in favour of a single nullable integer that handles
both cases: `None` = skip (not chronological), non-null = include and
sort.

## Consequences

**Positive:**
- Timeline generator (T3) has a clean, typed signal for both skip
  detection and ordering.
- No migration required for existing lesson graphs.
- Negative values accommodate BC dates and relative pre-epoch ordering.

**Negative:**
- Ingest paths do not populate `temporal_position` automatically; lesson
  graphs produced by the heuristic or LLM-refined chunker will have
  `None` for all concepts, causing the timeline generator to skip them.
  Population is deferred to T3 or a later phase.
- Integer ranks have no built-in insertion mechanism; inserting a new
  concept between two existing ranked concepts requires renumbering.
  Acceptable for phase 3; if it becomes painful, migrate to float ranks
  with a schema change and ADR.
