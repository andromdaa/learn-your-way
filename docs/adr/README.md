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
- [ADR-0006: `lyw_core` Sibling Package](./0006-lyw-core-package.md)
- [ADR-0007: Embedding Model — `sentence-transformers/all-MiniLM-L6-v2`](./0007-embedding-model.md)
- [ADR-0008: `ConceptNode.provenance` Field](./0008-concept-node-provenance.md)
- [ADR-0009: PersonalizationProfile as a Pydantic model](./0009-personalization-profile-schema.md)
- [ADR-0010: AssessmentItem.concept_id](./0010-assessment-item-concept-id.md)
- [ADR-0011: Validator Framework](./0011-validator-framework.md)
- [ADR-0012: AssessmentItem.correct_answer and bloom_level Fields](./0012-assessment-item-fields.md)
- [ADR-0013: Derived Asset Storage](./0013-derived-asset-storage.md)
- [ADR-0014: Add `temporal_position` to `ConceptNode`](./0014-temporal-position-field.md)
- [ADR-0015: Add `quiz_id` to track items belonging to a section quiz](./0015-quiz-id-tracking.md)
- [ADR-0016: Phase 2/3 scope reduction: strip in place to relevel + replace + profile](./0016-phase-2-3-scope-reduction.md)
- [ADR-0017: Worker Result Contract](./0017-worker-result-contract.md)
