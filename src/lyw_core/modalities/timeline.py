"""Timeline generator: pure graph-to-Mermaid conversion.

`TimelineGenerator` takes a `LessonGraph` plus a `PersonalizationProfile`
and emits Mermaid `timeline` diagram source from the lesson graph's
`ConceptNode` instances that have a non-None `temporal_position`.

If no concept in the graph has `temporal_position` set, the generator
returns a `TimelineSkipped` sentinel. The Arq job layer (T4) checks for
this sentinel and short-circuits without writing any asset.

Generation is deterministic from the lesson graph metadata added in T0c-r2.
No model call is made (see ADR-0011 and docs/plans/phase-3/T3-timeline-generator.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lesson_graph.models import LessonGraph, PersonalizationProfile


@dataclass(frozen=True)
class TimelineResult:
    """Result of a successful timeline generation.

    Attributes:
        mermaid: Mermaid ``timeline`` diagram source string.
        concept_ids: Ordered list of concept IDs (sorted by temporal_position
            ascending) that are included in the timeline.
    """

    mermaid: str
    concept_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TimelineSkipped:
    """Sentinel returned when the lesson graph has no temporal metadata.

    The Arq job layer checks for this type and skips persistence — there is
    no meaningful timeline to store for a lesson with no chronological order.
    """


class TimelineGenerator:
    """Pure graph-to-Mermaid timeline generator.

    The generator is stateless; a single instance can be reused across
    requests. No I/O, no model client, no persistence — the Arq job
    layer (T4) handles those concerns.
    """

    def generate(
        self,
        lesson_graph: LessonGraph,
        profile: PersonalizationProfile,
    ) -> TimelineResult | TimelineSkipped:
        """Emit Mermaid ``timeline`` source for ``lesson_graph``.

        Filters to concepts with a non-None ``temporal_position``, sorts
        them ascending by that value, and emits one ``section`` block per
        concept. Concept titles are used as section headers without
        fabricating any date strings; this satisfies the source-fidelity
        constraint.

        Args:
            lesson_graph: Source lesson graph.
            profile: Learner personalization profile (accepted for API parity
                with other modality generators; currently unused in pure-graph
                conversion).

        Returns:
            ``TimelineResult`` when at least one concept has
            ``temporal_position`` set; ``TimelineSkipped`` otherwise.
        """
        positioned = [
            c for c in lesson_graph.concepts if c.temporal_position is not None
        ]

        if not positioned:
            return TimelineSkipped()

        positioned.sort(key=lambda c: c.temporal_position if c.temporal_position is not None else 0)

        lines: list[str] = ["timeline"]
        concept_ids: list[str] = []

        for concept in positioned:
            concept_ids.append(concept.id)
            lines.append(f"    section {concept.title}")
            lines.append(f"        {concept.summary}")

        mermaid = "\n".join(lines) + "\n"
        return TimelineResult(mermaid=mermaid, concept_ids=concept_ids)
