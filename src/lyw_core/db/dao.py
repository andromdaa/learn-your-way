"""Async SQLite DAO for the source registry and lesson graph store."""

from __future__ import annotations

import importlib.resources
import json
from dataclasses import dataclass
from typing import Any

import aiosqlite
import structlog
from pydantic import ValidationError

from lesson_graph import ConceptNode, LessonGraph, SourceSpan
from lyw_core.profiles.models import LearnerProfile

log = structlog.get_logger()


LESSON_SCOPED_CONCEPT_ID: str = "__lesson__"
"""Sentinel ``concept_id`` for lesson-level generator kinds.

The ``derived_assets`` table requires ``concept_id TEXT NOT NULL``. Lesson-level
generators (which aggregate all or a pruned subset of concepts rather than a
single concept) use this constant instead of a real concept id.

Currently unused after ADR-0016 (modality + assessment generators removed);
retained for the step-5 cleanup that finally removes the constant.
"""


@dataclass
class DerivedAsset:
    """Metadata for a generator output persisted to the content-addressed store."""

    id: str
    lesson_id: str
    concept_id: str
    kind: str  # "relevel" | "replace"
    profile_id: str
    file_path: str
    created_at: str


@dataclass
class SourceRow:
    """Flattened source record with optional linked lesson_id."""

    doc_id: str
    path: str
    sha256: str
    created_at: str
    lesson_id: str | None


@dataclass
class LessonSummary:
    """Lesson list row — lesson metadata with aggregated concept count."""

    id: str
    source_id: str
    concept_count: int
    created_at: str


class Database:
    """Thin async wrapper around aiosqlite with schema bootstrapping."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    @classmethod
    async def connect(cls, path: str) -> Database:
        conn = await aiosqlite.connect(path)
        conn.row_factory = aiosqlite.Row
        db = cls(conn)
        await db._apply_schema()
        return db

    async def close(self) -> None:
        await self._conn.close()

    async def _apply_schema(self) -> None:
        pkg = importlib.resources.files("lyw_core.db")
        sql = (pkg / "schema.sql").read_text(encoding="utf-8")
        await self._conn.executescript(sql)

    # ------------------------------------------------------------------
    # Source registry
    # ------------------------------------------------------------------

    async def add_source(self, doc_id: str, path: str, sha256: str) -> None:
        await self._conn.execute(
            "INSERT INTO sources (doc_id, path, sha256) VALUES (?, ?, ?)",
            (doc_id, path, sha256),
        )
        await self._conn.commit()

    async def get_source(self, doc_id: str) -> dict[str, Any] | None:
        async with self._conn.execute(
            "SELECT doc_id, path, sha256, created_at FROM sources WHERE doc_id = ?",
            (doc_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def list_sources(self) -> list[SourceRow]:
        """Return all sources with the linked lesson_id (NULL if not ingested yet)."""
        async with self._conn.execute(
            """
            SELECT s.doc_id, s.path, s.sha256, s.created_at, l.id AS lesson_id
            FROM sources s
            LEFT JOIN lessons l ON l.source_id = s.doc_id
            ORDER BY s.created_at DESC
            """
        ) as cur:
            rows = await cur.fetchall()
        return [
            SourceRow(
                doc_id=row["doc_id"],
                path=row["path"],
                sha256=row["sha256"],
                created_at=row["created_at"],
                lesson_id=row["lesson_id"],
            )
            for row in rows
        ]

    async def get_source_row(self, doc_id: str) -> SourceRow | None:
        """Return a single SourceRow including linked lesson_id, or None."""
        async with self._conn.execute(
            """
            SELECT s.doc_id, s.path, s.sha256, s.created_at, l.id AS lesson_id
            FROM sources s
            LEFT JOIN lessons l ON l.source_id = s.doc_id
            WHERE s.doc_id = ?
            """,
            (doc_id,),
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        return SourceRow(
            doc_id=row["doc_id"],
            path=row["path"],
            sha256=row["sha256"],
            created_at=row["created_at"],
            lesson_id=row["lesson_id"],
        )

    # ------------------------------------------------------------------
    # LessonGraph persistence
    # ------------------------------------------------------------------

    async def upsert_lesson_graph(self, graph: LessonGraph) -> None:
        """Insert or replace a LessonGraph, replacing its concepts and spans."""
        async with self._conn.execute(
            "SELECT id FROM lessons WHERE id = ?", (graph.id,)
        ) as cur:
            exists = await cur.fetchone() is not None

        if exists:
            # Delete child rows; ON DELETE CASCADE handles spans.
            await self._conn.execute(
                "DELETE FROM concepts WHERE lesson_id = ?", (graph.id,)
            )
        else:
            await self._conn.execute(
                "INSERT INTO lessons (id, source_id) VALUES (?, ?)",
                (graph.id, graph.source_id),
            )

        for concept in graph.concepts:
            await self._conn.execute(
                """
                INSERT INTO concepts
                    (id, lesson_id, title, summary, learning_objective, prerequisites)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    concept.id,
                    graph.id,
                    concept.title,
                    concept.summary,
                    concept.learning_objective,
                    json.dumps(concept.prerequisites),
                ),
            )
            for span in concept.source_spans:
                await self._conn.execute(
                    """
                    INSERT INTO source_spans
                        (concept_id, doc_id, page_start, page_end, char_start, char_end)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        concept.id,
                        span.doc_id,
                        span.page_start,
                        span.page_end,
                        span.char_start,
                        span.char_end,
                    ),
                )

        await self._conn.commit()

    async def get_lesson_graph(self, lesson_id: str) -> LessonGraph | None:
        async with self._conn.execute(
            "SELECT id, source_id FROM lessons WHERE id = ?", (lesson_id,)
        ) as cur:
            lesson_row = await cur.fetchone()
        if lesson_row is None:
            return None

        async with self._conn.execute(
            """
            SELECT id, title, summary, learning_objective, prerequisites
            FROM concepts WHERE lesson_id = ?
            """,
            (lesson_id,),
        ) as cur:
            concept_rows = await cur.fetchall()

        concepts: list[ConceptNode] = []
        for crow in concept_rows:
            async with self._conn.execute(
                """
                SELECT doc_id, page_start, page_end, char_start, char_end
                FROM source_spans WHERE concept_id = ?
                """,
                (crow["id"],),
            ) as scur:
                span_rows = await scur.fetchall()

            spans = [
                SourceSpan(
                    doc_id=sr["doc_id"],
                    page_start=sr["page_start"],
                    page_end=sr["page_end"],
                    char_start=sr["char_start"],
                    char_end=sr["char_end"],
                )
                for sr in span_rows
            ]
            try:
                concepts.append(
                    ConceptNode(
                        id=crow["id"],
                        title=crow["title"],
                        summary=crow["summary"],
                        learning_objective=crow["learning_objective"],
                        source_spans=spans,
                        prerequisites=json.loads(crow["prerequisites"]),
                    )
                )
            except ValidationError:
                log.warning(
                    "dao.concept_skipped_invalid",
                    concept_id=crow["id"],
                    lesson_id=lesson_id,
                    span_count=len(spans),
                )

        return LessonGraph(
            id=lesson_row["id"],
            source_id=lesson_row["source_id"],
            concepts=concepts,
        )

    async def list_lessons(self) -> list[LessonSummary]:
        """Return all lessons ordered by creation date descending."""
        async with self._conn.execute(
            """
            SELECT l.id, l.source_id, l.created_at, COUNT(c.id) AS concept_count
            FROM lessons l
            LEFT JOIN concepts c ON c.lesson_id = l.id
            GROUP BY l.id
            ORDER BY l.created_at DESC
            """
        ) as cur:
            rows = await cur.fetchall()
        return [
            LessonSummary(
                id=row["id"],
                source_id=row["source_id"],
                concept_count=row["concept_count"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Learner profiles
    # ------------------------------------------------------------------

    async def add_profile(self, profile: LearnerProfile) -> None:
        """Upsert a learner profile by id."""
        await self._conn.execute(
            """
            INSERT INTO profiles (id, grade_level, interests, goals)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                grade_level = excluded.grade_level,
                interests   = excluded.interests,
                goals       = excluded.goals
            """,
            (
                profile.id,
                profile.grade_level,
                json.dumps(profile.interests),
                json.dumps(profile.goals),
            ),
        )
        await self._conn.commit()

    async def get_profile(self, profile_id: str) -> LearnerProfile | None:
        async with self._conn.execute(
            "SELECT id, grade_level, interests, goals FROM profiles WHERE id = ?",
            (profile_id,),
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        return LearnerProfile(
            id=row["id"],
            grade_level=row["grade_level"],
            interests=json.loads(row["interests"]),
            goals=json.loads(row["goals"]),
        )

    async def list_profiles(self) -> list[LearnerProfile]:
        async with self._conn.execute(
            "SELECT id, grade_level, interests, goals FROM profiles ORDER BY created_at"
        ) as cur:
            rows = await cur.fetchall()
        return [
            LearnerProfile(
                id=row["id"],
                grade_level=row["grade_level"],
                interests=json.loads(row["interests"]),
                goals=json.loads(row["goals"]),
            )
            for row in rows
        ]

    async def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile by id. Returns True if a row was deleted."""
        cur = await self._conn.execute(
            "DELETE FROM profiles WHERE id = ?", (profile_id,)
        )
        await self._conn.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Derived assets
    # ------------------------------------------------------------------

    async def save_derived_asset(self, asset: DerivedAsset) -> None:
        """Persist a DerivedAsset metadata row (INSERT OR IGNORE)."""
        await self._conn.execute(
            """
            INSERT OR IGNORE INTO derived_assets
                (id, lesson_id, concept_id, kind, profile_id, file_path)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                asset.id,
                asset.lesson_id,
                asset.concept_id,
                asset.kind,
                asset.profile_id,
                asset.file_path,
            ),
        )
        await self._conn.commit()

    async def get_derived_asset_by_id(self, asset_id: str) -> DerivedAsset | None:
        """Return a DerivedAsset by its primary key id, or None if not found."""
        async with self._conn.execute(
            """
            SELECT id, lesson_id, concept_id, kind, profile_id, file_path, created_at
            FROM derived_assets
            WHERE id = ?
            """,
            (asset_id,),
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        return DerivedAsset(
            id=row["id"],
            lesson_id=row["lesson_id"],
            concept_id=row["concept_id"],
            kind=row["kind"],
            profile_id=row["profile_id"],
            file_path=row["file_path"],
            created_at=row["created_at"],
        )

    async def get_derived_asset(
        self,
        lesson_id: str,
        concept_id: str,
        kind: str,
        profile_id: str,
    ) -> DerivedAsset | None:
        """Return the most-recently-created DerivedAsset for the given key, or None."""
        async with self._conn.execute(
            """
            SELECT id, lesson_id, concept_id, kind, profile_id, file_path, created_at
            FROM derived_assets
            WHERE lesson_id = ? AND concept_id = ? AND kind = ? AND profile_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (lesson_id, concept_id, kind, profile_id),
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        return DerivedAsset(
            id=row["id"],
            lesson_id=row["lesson_id"],
            concept_id=row["concept_id"],
            kind=row["kind"],
            profile_id=row["profile_id"],
            file_path=row["file_path"],
            created_at=row["created_at"],
        )

    async def list_derived_assets(
        self,
        lesson_id: str,
        *,
        concept_id: str | None = None,
        kind: str | None = None,
        profile_id: str | None = None,
    ) -> list[DerivedAsset]:
        """Return derived assets for a lesson, optionally filtered by concept/kind/profile."""
        params: list[str] = [lesson_id]
        where = "WHERE lesson_id = ?"
        if concept_id is not None:
            where += " AND concept_id = ?"
            params.append(concept_id)
        if kind is not None:
            where += " AND kind = ?"
            params.append(kind)
        if profile_id is not None:
            where += " AND profile_id = ?"
            params.append(profile_id)
        async with self._conn.execute(
            f"""
            SELECT id, lesson_id, concept_id, kind, profile_id, file_path, created_at
            FROM derived_assets
            {where}
            ORDER BY created_at DESC
            """,
            params,
        ) as cur:
            rows = await cur.fetchall()
        return [
            DerivedAsset(
                id=row["id"],
                lesson_id=row["lesson_id"],
                concept_id=row["concept_id"],
                kind=row["kind"],
                profile_id=row["profile_id"],
                file_path=row["file_path"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
