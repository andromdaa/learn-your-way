# ADR-0003: Arq over Celery

## Status

Accepted.

## Context

Modality generation (slides, mind maps, timelines) is asynchronous
and may take seconds to minutes per asset. Interactive paths (quiz
feedback, guided hints) run synchronously and must not be blocked by
generation jobs.

We need a job queue that:

- Pairs cleanly with FastAPI (asyncio).
- Has minimal operational footprint.
- Supports a single worker type (no complex routing).

## Decision

Use Arq, backed by Redis.

## Consequences

Positive:

- Asyncio-native: jobs are `async def` functions. No thread/process
  bridging needed to call async I/O (model API, Qdrant, SQLite via
  aiosqlite).
- One config file. No multi-broker, no result-backend, no flower-style
  monitoring infrastructure to set up.
- Redis is already in the stack (also used by Haystack's pipeline
  caches if enabled). One service handles both roles.

Negative:

- Smaller ecosystem than Celery. Fewer integrations and less
  documentation.
- No built-in retry policies as rich as Celery's. Acceptable; we
  retry at the validator layer rather than the queue layer.

## Alternatives considered

**Celery.** Industry standard. Right call when you have multiple
worker types, complex routing, multi-broker setups, or large teams
already familiar with it. We have none of those. Celery's
configuration surface and process model are overkill for one worker
running async generation jobs.

**RQ.** Simpler than Celery and battle-tested, but not asyncio-native.
We'd have to bridge sync workers to async pipelines. Arq removes that
seam.

**FastAPI BackgroundTasks.** In-process only. Generation jobs that
take minutes would tie up a request thread. Insufficient.
