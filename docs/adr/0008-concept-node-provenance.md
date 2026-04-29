# ADR-0008: `ConceptNode.provenance` Field

## Status

Accepted

## Context

Phase 1 introduces two chunking stages: a deterministic heuristic
chunker (T7) and an LLM-refined chunker (T9). Both emit `ConceptNode`
instances. Downstream consumers (inspection CLI, retrieval pipeline,
assessment generator) need to know which stage produced a given node
so they can apply different trust levels, display labels, or fallback
strategies.

The question is where to record this information: on the node itself,
in a separate metadata table, or implicitly via a wrapper type.

## Decision

Add `provenance: Literal["heuristic", "llm_refined"] = "heuristic"`
directly to `ConceptNode`.

The field defaults to `"heuristic"` so the schema change is
backward-compatible: existing serialised nodes are valid without
migration.

## Consequences

- Every node is self-describing. No join or wrapper is needed to
  determine its origin.
- The default prevents any node from being accidentally unlabelled:
  a node produced without an explicit `provenance` argument is
  conservatively treated as heuristic output.
- T9's LLM refiner must explicitly pass `provenance="llm_refined"`
  when it overwrites or supplements heuristic nodes.
- If a third provenance tier is introduced (e.g. human-curated), a
  new `Literal` value requires a schema change and a new ADR entry —
  intentional friction that keeps the vocabulary small.
