# ADR-0013 — Derived Asset Storage

## Status

Accepted (2026-04-30)

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
   `id`, `lesson_id`, `concept_id`, `kind` (`"relevel"` | `"replace"` |
   `"mnemonic"`), `profile_id`, `file_path`, `created_at`.

Generators remain pure (return text only). A thin `save_derived_asset`
helper in the DAO writes both stores after the generator returns. The
`personalize_concept` Arq job calls the generator then the helper,
keeping each layer single-responsibility.

## Consequences

- `DerivedAsset` is a plain dataclass in `lyw_core/db/dao.py` — no
  `SCHEMA_CHANGE=1` required.
- `get_derived_asset(lesson_id, concept_id, kind, profile_id)` lets the
  API serve cached content without re-running the generator.
- Content-addressed storage means re-generating identical text writes
  nothing new to disk.
