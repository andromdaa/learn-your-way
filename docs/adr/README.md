# Architecture Decision Records

ADRs capture the rationale behind architectural and stack-level
decisions. They are immutable once accepted: revisions happen by
adding a new ADR that supersedes the prior one, not by editing
history.

Each ADR has the structure:

- **Status** (Accepted / Superseded by ADR-NNNN / Deprecated)
- **Context** — what problem we faced and why it matters
- **Decision** — what we chose
- **Consequences** — positive and negative outcomes we accept
- **Alternatives considered** — what we rejected and why

The numbering is monotonic. Once an ADR is committed, its filename
and number do not change.

## Index

- [ADR-0001: Haystack with Qdrant + InMemoryBM25 over Vespa or
  OpenSearch](./0001-haystack-over-vespa.md)
- [ADR-0002: SQLite over Postgres](./0002-sqlite-over-postgres.md)
- [ADR-0003: Arq over Celery](./0003-arq-over-celery.md)
- [ADR-0004: Local filesystem over object storage](./0004-local-fs-over-s3.md)
- [ADR-0005: Ollama-first model serving with API
  fallback](./0005-ollama-first-model-serving.md)
