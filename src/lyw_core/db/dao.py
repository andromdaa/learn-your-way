"""Async SQLite DAO for the source registry and lesson graph store."""

from __future__ import annotations

import importlib.resources
import json
import uuid
from dataclasses import dataclass
from typing import Any

import aiosqlite

from lesson_graph import AssessmentItem, ConceptNode, LessonGraph, SourceSpan
from lyw_core.profiles.models import LearnerProfile


@dataclass
class AttemptRecord:
    """A single learner attempt at an assessment item."""

    id: str
    profile_id: str
    item_id: str
    response: str
    correct: bool
    attempted_at: str


@dataclass
class DerivedAsset:
    """Metadata for a generator output persisted to the content-addressed store."""

    id: str
    lesson_id: str
    concept_id: str
    kind: str  # "relevel" | "replace" | "mnemonic"
    profile_id: str
    file_path: str
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

    # ------------------------------------------------------------------
    # Assessment items
    # ------------------------------------------------------------------

    async def add_assessment_item(self, item: AssessmentItem) -> None:
        """Persist a single AssessmentItem; source_spans serialised as JSON."""
        await self._conn.execute(
            """
            INSERT INTO assessment_items
                (id, concept_id, kind, prompt, rationale,
                 difficulty, correct_answer, bloom_level, source_spans, quiz_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.id,
                item.concept_id,
                item.kind,
                item.prompt,
                item.rationale,
                item.difficulty,
                item.correct_answer,
                item.bloom_level,
                json.dumps([s.model_dump() for s in item.source_spans]),
                item.quiz_id,
            ),
        )
        await self._conn.commit()

    async def get_lesson_id_by_concept_id(self, concept_id: str) -> str | None:
        """Return the lesson_id that owns the given concept, or None if not found."""
        async with self._conn.execute(
            "SELECT lesson_id FROM concepts WHERE id = ?",
            (concept_id,),
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        return str(row["lesson_id"])

    async def get_items_by_concept(self, concept_id: str) -> list[AssessmentItem]:
        """Return every AssessmentItem stored for the given concept (insertion order)."""
        async with self._conn.execute(
            """
            SELECT id, concept_id, kind, prompt, rationale,
                   difficulty, correct_answer, bloom_level, source_spans, quiz_id
            FROM assessment_items
            WHERE concept_id = ?
            ORDER BY rowid
            """,
            (concept_id,),
        ) as cur:
            rows = await cur.fetchall()

        items: list[AssessmentItem] = []
        for row in rows:
            spans = [SourceSpan(**d) for d in json.loads(row["source_spans"])]
            items.append(
                AssessmentItem(
                    id=row["id"],
                    concept_id=row["concept_id"],
                    kind=row["kind"],
                    prompt=row["prompt"],
                    rationale=row["rationale"],
                    difficulty=row["difficulty"],
                    correct_answer=row["correct_answer"],
                    bloom_level=row["bloom_level"],
                    source_spans=spans,
                    quiz_id=row["quiz_id"],
                )
            )
        return items

    async def get_item_by_id(self, item_id: str) -> AssessmentItem | None:
        """Return a single AssessmentItem by its primary key, or None."""
        async with self._conn.execute(
            """
            SELECT id, concept_id, kind, prompt, rationale,
                   difficulty, correct_answer, bloom_level, source_spans, quiz_id
            FROM assessment_items
            WHERE id = ?
            """,
            (item_id,),
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        spans = [SourceSpan(**d) for d in json.loads(row["source_spans"])]
        return AssessmentItem(
            id=row["id"],
            concept_id=row["concept_id"],
            kind=row["kind"],
            prompt=row["prompt"],
            rationale=row["rationale"],
            difficulty=row["difficulty"],
            correct_answer=row["correct_answer"],
            bloom_level=row["bloom_level"],
            source_spans=spans,
            quiz_id=row["quiz_id"],
        )

    async def get_items_by_quiz_id(self, quiz_id: str) -> list[AssessmentItem]:
        """Return every AssessmentItem stored with the given quiz_id (insertion order)."""
        async with self._conn.execute(
            """
            SELECT id, concept_id, kind, prompt, rationale,
                   difficulty, correct_answer, bloom_level, source_spans, quiz_id
            FROM assessment_items
            WHERE quiz_id = ?
            ORDER BY rowid
            """,
            (quiz_id,),
        ) as cur:
            rows = await cur.fetchall()

        items: list[AssessmentItem] = []
        for row in rows:
            spans = [SourceSpan(**d) for d in json.loads(row["source_spans"])]
            items.append(
                AssessmentItem(
                    id=row["id"],
                    concept_id=row["concept_id"],
                    kind=row["kind"],
                    prompt=row["prompt"],
                    rationale=row["rationale"],
                    difficulty=row["difficulty"],
                    correct_answer=row["correct_answer"],
                    bloom_level=row["bloom_level"],
                    source_spans=spans,
                    quiz_id=row["quiz_id"],
                )
            )
        return items

    # ------------------------------------------------------------------
    # Attempts
    # ------------------------------------------------------------------

    async def record_attempt(
        self,
        profile_id: str,
        item_id: str,
        response: str,
        correct: bool,
    ) -> None:
        """Persist a single learner attempt; id and attempted_at are
        generated server-side."""
        attempt_id = str(uuid.uuid4())
        await self._conn.execute(
            """
            INSERT INTO attempts (id, profile_id, item_id, response, correct)
            VALUES (?, ?, ?, ?, ?)
            """,
            (attempt_id, profile_id, item_id, response, int(correct)),
        )
        await self._conn.commit()

    async def get_attempts_by_quiz_id(
        self, quiz_id: str, profile_id: str
    ) -> list[AttemptRecord]:
        """Return all attempts by a profile for items belonging to a quiz.

        Uses a JOIN through assessment_items on quiz_id so callers do not
        need to iterate all profile attempts manually.
        """
        async with self._conn.execute(
            """
            SELECT a.id, a.profile_id, a.item_id, a.response, a.correct, a.attempted_at
            FROM attempts a
            JOIN assessment_items ai ON ai.id = a.item_id
            WHERE ai.quiz_id = ? AND a.profile_id = ?
            ORDER BY a.attempted_at ASC
            """,
            (quiz_id, profile_id),
        ) as cur:
            rows = await cur.fetchall()
        return [
            AttemptRecord(
                id=row["id"],
                profile_id=row["profile_id"],
                item_id=row["item_id"],
                response=row["response"],
                correct=bool(row["correct"]),
                attempted_at=row["attempted_at"],
            )
            for row in rows
        ]

    async def get_profile_attempts(self, profile_id: str) -> list[AttemptRecord]:
        """Return all attempts for a profile, ordered by attempted_at ASC."""
        async with self._conn.execute(
            """
            SELECT id, profile_id, item_id, response, correct, attempted_at
            FROM attempts
            WHERE profile_id = ?
            ORDER BY attempted_at ASC
            """,
            (profile_id,),
        ) as cur:
            rows = await cur.fetchall()
        return [
            AttemptRecord(
                id=row["id"],
                profile_id=row["profile_id"],
                item_id=row["item_id"],
                response=row["response"],
                correct=bool(row["correct"]),
                attempted_at=row["attempted_at"],
            )
            for row in rows
        ]

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
