# Plans

In-flight checklists that mirror the phase specs. Plans are the
working surface for active development. Specs in `specs/` are stable
contracts; plans here are mutable.

When a phase opens, copy the corresponding spec's deliverables into a
new plan file, work the boxes, and record decisions inline as they
are made. When the phase ships, archive the plan (don't delete it)
and close out by reconciling any spec drift.

## Conventions

- One plan per active phase.
- Filename pattern: `phase-N-<short-name>-tracker.md`.
- Audit follow-ups live under `audits/<short-name>/` with a README index plus one file per initiative.
- Decisions made during implementation that affect the phase contract
  go back into the relevant `specs/` file via PR; the plan records
  the fact and the date.
- Decisions that are stack- or architecture-level become ADRs.
