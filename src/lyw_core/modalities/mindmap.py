"""Mind-map generator: pure graph-to-Mermaid conversion.

`MindMapGenerator` takes a `LessonGraph` plus a `PersonalizationProfile`
and emits a Mermaid `flowchart TD` source string. No model call is made;
Mermaid source is deterministic from the lesson graph (see ADR-0011 and
docs/plans/phase-3/T1-mindmap-generator.md).

Pruning is BFS over `ConceptNode.prerequisites` edges from a focal
concept, capped at `max_nodes`. The focal concept defaults to the
concept with the most prerequisites (first-wins on ties); callers can
override via `focal_concept_id`. Visited tracking guards against the
prerequisite-cycle case (the schema does not enforce DAG-ness).
"""

from __future__ import annotations

import re
from collections import deque

from lesson_graph.models import ConceptNode, LessonGraph, PersonalizationProfile

_NON_ALNUM = re.compile(r"[^A-Za-z0-9]")


def _sanitize_node_id(raw_id: str) -> str:
    """Replace any non-alphanumeric character with `_` so Mermaid accepts it."""
    return _NON_ALNUM.sub("_", raw_id)


def _escape_label(title: str) -> str:
    """Escape double quotes in a node title for safe inclusion in Mermaid."""
    return title.replace('"', '\\"')


class MindMapGenerator:
    """Pure graph-to-Mermaid mind-map generator.

    The generator is stateless; a single instance can be reused across
    requests. No I/O, no model client, no persistence — the Arq job
    layer (T2) handles those concerns.
    """

    def generate(
        self,
        lesson_graph: LessonGraph,
        profile: PersonalizationProfile,
        focal_concept_id: str | None = None,
        max_nodes: int = 20,
    ) -> str:
        """Emit Mermaid `flowchart TD` source for `lesson_graph`.

        Args:
            lesson_graph: Source lesson graph.
            profile: Learner personalization profile (API parity with other
                modality generators; currently unused in pure-graph conversion).
            focal_concept_id: Optional override for the BFS root. When
                None, the concept with the most prerequisites is chosen
                (first-wins on ties).
            max_nodes: Hard cap on emitted nodes (default 20). Pruning
                proceeds breadth-first from the focal concept.

        Returns:
            A Mermaid source string starting with ``flowchart TD\\n``.

        Raises:
            ValueError: If ``lesson_graph.concepts`` is empty, or if
                ``focal_concept_id`` is provided but not present in the graph.
        """
        concepts = lesson_graph.concepts
        if not concepts:
            raise ValueError("lesson_graph.concepts is empty; cannot build mind map")

        index: dict[str, ConceptNode] = {c.id: c for c in concepts}

        if focal_concept_id is not None:
            if focal_concept_id not in index:
                raise ValueError(
                    f"focal_concept_id '{focal_concept_id}' not found in lesson graph"
                )
            focal = index[focal_concept_id]
        else:
            focal = max(concepts, key=lambda c: len(c.prerequisites))

        selected_ids = self._bfs_select(focal, index, max_nodes)

        lines: list[str] = ["flowchart TD"]
        for cid in selected_ids:
            node = index[cid]
            lines.append(f'    {_sanitize_node_id(cid)}["{_escape_label(node.title)}"]')

        for cid in selected_ids:
            node = index[cid]
            for prereq_id in node.prerequisites:
                if prereq_id in selected_ids and prereq_id in index:
                    lines.append(
                        f"    {_sanitize_node_id(prereq_id)} --> "
                        f"{_sanitize_node_id(cid)}"
                    )

        return "\n".join(lines) + "\n"

    @staticmethod
    def _bfs_select(
        focal: ConceptNode,
        index: dict[str, ConceptNode],
        max_nodes: int,
    ) -> list[str]:
        """BFS over prerequisite edges from `focal`, cycle-safe.

        Returns concept IDs in BFS insertion order, capped at `max_nodes`.
        The focal concept is always included (position 0) regardless of the cap.
        """
        if max_nodes <= 0:
            return [focal.id]

        visited: set[str] = {focal.id}
        order: list[str] = [focal.id]
        queue: deque[ConceptNode] = deque([focal])

        while queue and len(order) < max_nodes:
            current = queue.popleft()
            for prereq_id in current.prerequisites:
                if len(order) >= max_nodes:
                    break
                if prereq_id in visited or prereq_id not in index:
                    continue
                visited.add(prereq_id)
                order.append(prereq_id)
                queue.append(index[prereq_id])

        return order
