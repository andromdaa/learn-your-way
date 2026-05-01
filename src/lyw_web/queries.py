"""Read-only SQLite queries for the browser test harness.

Opens its own aiosqlite connection, separate from lyw_core's Database, so
lyw_core/db/dao.py is not modified.  All methods are read-only.
"""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite


@dataclass
class LessonSummary:
    id: str
    source_id: str
    concept_count: int
    created_at: str


@dataclass
class AssetRow:
    id: str
    lesson_id: str
    concept_id: str
    kind: str
    profile_id: str
    file_path: str
    created_at: str


class WebQueries:
    """Thin read-only accessor for UI-specific listing queries."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    @classmethod
    async def connect(cls, path: str) -> WebQueries:
        conn = await aiosqlite.connect(path)
        conn.row_factory = aiosqlite.Row
        return cls(conn)

    async def close(self) -> None:
        await self._conn.close()

    async def list_lessons(self) -> list[LessonSummary]:
        async with self._conn.execute(
            """
            SELECT l.id, l.source_id, l.created_at,
                   COUNT(c.id) AS concept_count
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

    async def list_derived_assets(self, lesson_id: str) -> list[AssetRow]:
        async with self._conn.execute(
            """
            SELECT id, lesson_id, concept_id, kind, profile_id, file_path, created_at
            FROM derived_assets
            WHERE lesson_id = ?
            ORDER BY created_at DESC
            """,
            (lesson_id,),
        ) as cur:
            rows = await cur.fetchall()
        return [
            AssetRow(
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
