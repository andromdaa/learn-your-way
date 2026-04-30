"""Gap detector: rule-based prerequisite gap detection.

Algorithm (per T12 spec):
1. Load all attempts for the profile; filter to incorrect ones.
2. For the most recent incorrect attempt, look up the concept_id from
   assessment_items via the DAO.
3. Retrieve the ConceptNode for that concept_id from the lesson graph.
4. Walk concept.prerequisites in list order (index 0 = highest priority, per
   ADR-0012) and return the first prerequisite ConceptNode for which the
   learner has no correct attempt.
5. If all prerequisites are mastered, there are no prerequisites, or there are
   no incorrect attempts, return None.

No vector lookup, no embedding-based similarity (out of scope until later phase).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import structlog

if TYPE_CHECKING:
    from lesson_graph import ConceptNode, LessonGraph
    from lyw_core.db.dao import AttemptRecord

log = structlog.get_logger(__name__)


class _DaoProtocol(Protocol):
    """Structural protocol for the DAO subset used by GapDetector."""

    async def get_profile_attempts(self, profile_id: str) -> list[AttemptRecord]: ...

    async def get_item_by_id(self, item_id: str) -> object | None: ...


class GapDetector:
    """Rule-based gap detector.

    Stateless: all state is passed in via arguments so the detector can be
    used in both request-scoped and background contexts without holding a
    long-lived DAO reference.
    """

    async def next_concept(
        self,
        profile_id: str,
        lesson_graph: LessonGraph,
        dao: _DaoProtocol,
    ) -> ConceptNode | None:
        """Return the highest-priority unmastered prerequisite concept for the
        learner's most recent incorrect attempt, or None if no gap is found.

        Args:
            profile_id: Learner profile id.
            lesson_graph: The canonical lesson graph to look up concepts.
            dao: DAO with get_profile_attempts and get_item_by_id.

        Returns:
            The ConceptNode to revisit, or None.
        """
        attempts = await dao.get_profile_attempts(profile_id)

        if not attempts:
            return None

        # Collect mastered concept ids: any concept for which the learner has
        # at least one correct attempt.
        mastered_concept_ids: set[str] = set()
        incorrect_attempts: list[AttemptRecord] = []

        for attempt in attempts:
            item = await dao.get_item_by_id(attempt.item_id)
            if item is None:
                log.warning(
                    "gap_detector.item_not_found",
                    item_id=attempt.item_id,
                    profile_id=profile_id,
                )
                continue
            # item is AssessmentItem at runtime; use getattr for protocol compat
            concept_id: str = getattr(item, "concept_id", "")
            if attempt.correct:
                mastered_concept_ids.add(concept_id)
            else:
                incorrect_attempts.append(attempt)

        if not incorrect_attempts:
            return None

        # Most recent incorrect attempt: attempts are ordered by attempted_at
        # ASC by the DAO; the last element is the most recent.
        most_recent = max(incorrect_attempts, key=lambda a: a.attempted_at)

        item = await dao.get_item_by_id(most_recent.item_id)
        if item is None:
            return None

        concept_id = getattr(item, "concept_id", "")

        # Look up the concept in the lesson graph.
        concept_map: dict[str, ConceptNode] = {c.id: c for c in lesson_graph.concepts}
        concept = concept_map.get(concept_id)
        if concept is None:
            log.warning(
                "gap_detector.concept_not_in_graph",
                concept_id=concept_id,
                profile_id=profile_id,
            )
            return None

        # Walk prerequisites in priority order (index 0 = highest priority).
        for prereq_id in concept.prerequisites:
            if prereq_id not in mastered_concept_ids:
                prereq_node = concept_map.get(prereq_id)
                if prereq_node is not None:
                    return prereq_node

        return None
