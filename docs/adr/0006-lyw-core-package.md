# ADR-0006: `lyw_core` Sibling Package

## Status

Accepted

## Context

Phase 1 needs a stable canonical lesson graph while later tasks add
application behavior such as parsing, storage, retrieval, workers, and
API endpoints. The schema and protocols are shared across those layers,
but application code should not make the canonical graph package harder
to audit for source-fidelity invariants.

The existing project already uses `src/lesson_graph` for schema models
and related interfaces. T0c establishes `src/lyw_core` as the sibling
package for application code.

## Decision

Keep `lesson_graph` focused on canonical schema and protocol types.
Put Phase 1 application code in `lyw_core`.

Both packages are included in the wheel build and type-check targets.

## Consequences

- Schema invariants remain isolated in `lesson_graph`.
- Later Phase 1 tasks have a clear home for parsing, storage, retrieval,
  worker, and API code.
- Import direction should favor `lyw_core` depending on `lesson_graph`,
  not the reverse.
- T0c adds no application behavior; it only establishes the package
  boundary and test layout needed by later tasks.
