# ADR-0002: SQLite over Postgres

## Status

Accepted.

## Context

We need a relational store for lesson metadata, learner profile,
assessment items, attempts, and asset references. The deployment is
single-user, single-machine.

## Decision

Use SQLite as the relational store. The database file lives in the
configured data directory.

## Consequences

Positive:

- Zero operational overhead. No daemon, no auth, no networking, no
  user management.
- Atomic file backups: copy the data directory to back up the entire
  application state.
- Embeddable in tests: in-memory SQLite gives fast, isolated test
  fixtures.
- Sufficient performance. Single-user write throughput is far below
  SQLite's ceiling.

Negative:

- Concurrent writers are limited (one writer at a time). Acceptable
  at single-user scale.
- No native horizontal scaling. Out of scope for this project.
- Some advanced query features (window function variants, JSON
  ergonomics) are weaker than Postgres. None are required by the
  current data model.

## Alternatives considered

**Postgres.** Right call when you have multiple writers, replication,
or schema features that exceed SQLite. We have none of those. Running
a Postgres server for one user is a maintenance tax with no benefit.

**DuckDB.** Strong for analytical workloads. Our access pattern is
OLTP-shaped (small reads and writes per learner action), which is
SQLite's home turf.
