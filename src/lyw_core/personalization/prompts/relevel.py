"""Prompt builder for the re-leveling generator."""

from __future__ import annotations

from lesson_graph.interfaces import ChatMessage
from lesson_graph.models import ConceptNode
from lyw_core.profiles.models import LearnerProfile


def build_relevel_messages(
    concept: ConceptNode, profile: LearnerProfile
) -> list[ChatMessage]:
    """Build chat messages that instruct the model to re-level a concept summary.

    The prompt preserves all facts, terminology, and structure; only sentence
    complexity and word choice may change.
    """
    return [
        {
            "role": "system",
            "content": (
                "You are an educational text editor. "
                f"Rewrite the following concept summary to target reading grade {profile.grade_level}. "
                "Preserve all facts, technical terminology, and logical structure exactly. "
                "Only adjust sentence complexity and word choice to match the target grade. "
                "Return only the rewritten text with no preamble or explanation."
            ),
        },
        {
            "role": "user",
            "content": concept.summary,
        },
    ]
