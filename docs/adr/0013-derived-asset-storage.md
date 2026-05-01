# ADR-0013 — Derived Asset Storage

## Status

Accepted (2026-04-30)
Amended (2026-04-30): removed stale phase-2 `kind` enumeration; valid values
are now defined by the `DerivedAsset.kind` Literal in
`src/lesson_graph/models.py`.
Amended (2026-05-01): two-DerivedAsset pattern retained with documented
rationale (see below).

## Context

The three personalization generators (`ReLeveler`, `ExampleReplacer`,
`MnemonicGenerator`) return text but never persist it. The caller drops
the return value, so generated content is lost after each request and
cannot be served again without regenerating it (expensive, non-deterministic).
The API needs a way to retrieve previously generated content for a given
(lesson, concept, kind, profile) tuple.

## Decision

Use two complementary stores:

1. **Content-addressed file storage** via the existing
   `DataDir.write_asset(data, suffix=".txt")`. This deduplicates
   identical content automatically (SHA-256 addressed) and keeps binary
   blobs off the database.

2. **`derived_assets` SQLite table** for queryable metadata:
   `id`, `lesson_id`, `concept_id`, `kind`, `profile_id`, `file_path`,
   `created_at`. Valid `kind` values are defined by the `DerivedAsset.kind`
   Literal in `src/lesson_graph/models.py` (and must agree with the DAO
   dataclass at `src/lyw_core/db/dao.py`).

Generators remain pure (return text only). A thin `save_derived_asset`
helper in the DAO writes both stores after the generator returns. The
`personalize_concept` Arq job calls the generator then the helper,
keeping each layer single-responsibility.

### Amendment (2026-05-01) — two-DerivedAsset pattern

Two `DerivedAsset` types coexist and are intentionally distinct:

- **`lesson_graph.models.DerivedAsset`** (Pydantic): the generator-output
  domain model. Carries `based_on_concepts: list[str]` (multi-concept
  provenance) and a full `PersonalizationProfile`. Used in the domain layer
  and tests.

- **`lyw_core.db.dao.DerivedAsset`** (plain dataclass): the persistence
  record. Carries scalar `concept_id`, `profile_id`, `file_path`, and
  `created_at`. Used in the DAO and API layers.

The split is load-bearing: the Pydantic type records rich provenance (which
concepts contributed to the output) while the DAO type stores the minimal
keys needed for lookup and serving. Collapsing them would lose the
multi-concept `based_on_concepts` list or force it into the database schema.
The step-5 cleanup confirmed the split remains justified even after the
modality generators were removed; the surviving `immersive_text` kind
benefits from the provenance field.

## Consequences

- `DerivedAsset` is a plain dataclass in `lyw_core/db/dao.py` — no
  `SCHEMA_CHANGE=1` required.
- `get_derived_asset(lesson_id, concept_id, kind, profile_id)` lets the
  API serve cached content without re-running the generator.
- Content-addressed storage means re-generating identical text writes
  nothing new to disk.
- The two-type split requires the `personalize_concept` job to construct
  the DAO record explicitly rather than deriving it from the domain model.
  This is intentional; the job is the single place that owns both writes.
