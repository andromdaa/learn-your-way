-- SQLite schema for the source registry and lesson metadata.
-- Apply once via Database.connect(); idempotent (CREATE TABLE IF NOT EXISTS).

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    doc_id      TEXT PRIMARY KEY,
    path        TEXT NOT NULL,
    sha256      TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS lessons (
    id          TEXT PRIMARY KEY,
    source_id   TEXT NOT NULL REFERENCES sources(doc_id),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS concepts (
    id                  TEXT PRIMARY KEY,
    lesson_id           TEXT NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    summary             TEXT NOT NULL,
    learning_objective  TEXT NOT NULL,
    -- Ordered list of prerequisite concept IDs serialised as a JSON array.
    prerequisites       TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS source_spans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id  TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    doc_id      TEXT NOT NULL,
    page_start  INTEGER NOT NULL,
    page_end    INTEGER NOT NULL,
    char_start  INTEGER NOT NULL,
    char_end    INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lessons_source_id ON lessons(source_id);
CREATE INDEX IF NOT EXISTS idx_concepts_lesson_id ON concepts(lesson_id);
CREATE INDEX IF NOT EXISTS idx_source_spans_concept_id ON source_spans(concept_id);

CREATE TABLE IF NOT EXISTS profiles (
    id          TEXT PRIMARY KEY,
    grade_level TEXT NOT NULL,
    interests   TEXT NOT NULL DEFAULT '[]',
    goals       TEXT NOT NULL DEFAULT '[]',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS assessment_items (
    id              TEXT PRIMARY KEY,
    concept_id      TEXT NOT NULL REFERENCES concepts(id),
    kind            TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    rationale       TEXT NOT NULL,
    difficulty      TEXT NOT NULL,
    correct_answer  TEXT,
    bloom_level     TEXT,
    source_spans    TEXT NOT NULL,
    quiz_id         TEXT
);

CREATE INDEX IF NOT EXISTS idx_assessment_items_concept_id ON assessment_items(concept_id);

CREATE TABLE IF NOT EXISTS attempts (
    id              TEXT PRIMARY KEY,
    profile_id      TEXT NOT NULL REFERENCES profiles(id),
    item_id         TEXT NOT NULL REFERENCES assessment_items(id),
    response        TEXT NOT NULL,
    correct         INTEGER NOT NULL,
    attempted_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    quiz_id         TEXT
);

CREATE INDEX IF NOT EXISTS idx_attempts_profile_id ON attempts(profile_id);

CREATE TABLE IF NOT EXISTS derived_assets (
    id          TEXT PRIMARY KEY,
    lesson_id   TEXT NOT NULL,
    concept_id  TEXT NOT NULL,
    kind        TEXT NOT NULL,
    profile_id  TEXT NOT NULL,
    file_path   TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_derived_assets_lookup
    ON derived_assets(lesson_id, concept_id, kind, profile_id);
