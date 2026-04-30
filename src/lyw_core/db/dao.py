"""Async SQLite DAO for the source registry and lesson graph store."""

from __future__ import annotations

import importlib.resources
import json
from typing import Any

import aiosqlite

from lesson_graph import ConceptNode, LessonGraph, SourceSpan
from lyw_core.profiles.models import LearnerProfile


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

        return LessonGraph(
            id=lesson_row["id"],
            source_id=lesson_row["source_id"],
            concepts=concepts,
        )

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
