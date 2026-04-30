"""Prompt builders for the slide generator.

Two builders:
- ``build_slide_outline_messages``: requests a JSON outline with one item per
  concept (title, key points, concept_id).
- ``build_slide_body_messages``: requests body text and speaker notes for a
  single outline item.

Both builders follow the no-fabrication rule: the model is explicitly told
to derive all content from the provided concept summaries and key points.
"""

from __future__ import annotations

from lesson_graph.interfaces import ChatMessage
from lesson_graph.models import LessonGraph, PersonalizationProfile

_OUTLINE_SYSTEM = (
    "You are an educational slide deck author. Your job is to produce a structured "
    "outline for a slide deck based on the lesson concepts provided.\n\n"
    "Rules:\n"
    "  - Every slide must be directly grounded in the provided concept summaries.\n"
    "  - Do not invent facts not present in the summaries.\n"
    "  - Each outline item covers exactly one concept.\n\n"
    "Return a JSON array (and ONLY a JSON array, no preamble, no trailing text) "
    "where each element is an object with these exact keys:\n"
    '  "title": a concise slide title (non-empty string),\n'
    '  "key_points": a list of 2-4 key point strings for this slide,\n'
    '  "concept_id": the concept id string from the input.\n\n'
    "If no meaningful slide can be made for a concept, omit it from the array."
)

_BODY_SYSTEM = (
    "You are an educational slide deck author. Flesh out a single slide from the "
    "provided outline item and concept summary.\n\n"
    "Rules:\n"
    "  - All content must be grounded in the concept summary. Do not invent facts.\n"
    "  - The body should be clear, concise prose suitable for a presentation slide.\n"
    "  - Speaker notes should provide extra context for the presenter.\n\n"
    "Return a JSON object (and ONLY a JSON object, no preamble, no trailing text) "
    "with these exact keys:\n"
    '  "body": the slide body text (non-empty string),\n'
    '  "speaker_notes": the speaker notes text (non-empty string).\n'
)


def build_slide_outline_messages(
    lesson_graph: LessonGraph,
    profile: PersonalizationProfile,
) -> list[ChatMessage]:
    """Build messages requesting a JSON outline of slides for the lesson."""
    concept_lines = []
    for c in lesson_graph.concepts:
        concept_lines.append(
            f"- concept_id: {c.id!r}\n  title: {c.title!r}\n  summary: {c.summary!r}"
        )
    concepts_text = "\n".join(concept_lines)

    user_content = (
        f"Grade level: {profile.grade_level}\n"
        f"Learner interests: {', '.join(profile.interests)}\n\n"
        f"Lesson concepts:\n{concepts_text}"
    )
    return [
        {"role": "system", "content": _OUTLINE_SYSTEM},
        {"role": "user", "content": user_content},
    ]


def build_slide_body_messages(
    outline_title: str,
    key_points: list[str],
) -> list[ChatMessage]:
    """Build messages requesting body + speaker notes for one slide.

    Args:
        outline_title: The slide title from the outline step.
        key_points: Key points for this slide from the outline step.
    """
    key_points_text = "\n".join(f"  - {kp}" for kp in key_points)
    user_content = (
        f"Slide title: {outline_title!r}\nKey points to cover:\n{key_points_text}"
    )
    return [
        {"role": "system", "content": _BODY_SYSTEM},
        {"role": "user", "content": user_content},
    ]
