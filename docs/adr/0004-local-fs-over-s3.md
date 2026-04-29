# ADR-0004: Local filesystem over object storage

## Status

Accepted.

## Context

We need to store source PDFs and derived assets (slide decks, mind
map source, timelines, immersive text exports). The deployment is a
single self-hosted machine.

## Decision

Store files on the local filesystem under a configurable data
directory. The directory layout is part of the phase 1 spec.

## Consequences

Positive:

- No additional service. No credentials, no networking, no SDKs.
- Backups are filesystem-level: `tar`, `rsync`, or btrfs snapshots
  cover both the SQLite database and the asset tree.
- Direct streaming to FastAPI responses without a proxy layer.

Negative:

- Single-machine binding. Moving the deployment requires moving the
  data directory.
- No native versioning. Asset versioning is handled at the
  application layer (content-hashed filenames).

## Alternatives considered

**S3 / MinIO / Garage.** Right call when multiple machines need
shared storage, when files exceed local disk, or when the workload
benefits from object lifecycle policies. None apply here. Running an
object store for one user is operational overhead with no payoff.

**Database BLOBs.** Convenient for transactional consistency but
turns the database into a bottleneck for large binary assets and
makes backups slower. The mixed-concern pattern (SQLite for metadata,
filesystem for blobs) is well-trodden and avoids both problems.
