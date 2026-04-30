"""Prompt builder for the Glows/Grows feedback generator.

This prompt is NOT subject to source faithfulness validation because
it produces meta-commentary on learner performance, not educational
claims about subject matter. See docs/plans/phase-2/T9-section-quiz.md.
"""

from __future__ import annotations

import dataclasses
import json

from lesson_graph.interfaces import ChatMessage
from lesson_graph.models import AssessmentItem
from lyw_core.db.dao import AttemptRecord

_SYSTEM_PROMPT = (
    "You are a supportive tutor delivering feedback on a learner's quiz attempt. "
    "Write two short feedback paragraphs:\n\n"
    "  Glows: 1-3 sentences highlighting specific strengths shown in the attempts.\n"
    "  Grows: 1-3 sentences identifying concrete areas to improve, with a suggestion.\n\n"
    "Tone: encouraging but specific. Do not invent facts about the subject matter.\n\n"
    "Return ONLY a JSON object (no preamble, no trailing text) with exactly two "
    'string keys: "glows" and "grows".\n'
    'Example: {"glows": "You correctly identified...", "grows": "Consider reviewing..."}'
)


def build_glows_grows_messages(
    items: list[AssessmentItem],
    attempts: list[AttemptRecord],
) -> list[ChatMessage]:
    """Build chat messages asking the model for Glows/Grows feedback."""
    pairs: list[str] = []
    for i, item in enumerate(items):
        attempt_dict = dataclasses.asdict(attempts[i]) if i < len(attempts) else {}
        pairs.append(
            f"Question: {item.prompt}\n"
            f"Concept: {item.concept_id}\n"
            f"Correct answer: {item.correct_answer}\n"
            f"Bloom level: {item.bloom_level}\n"
            f"Attempt: {json.dumps(attempt_dict)}"
        )

    if pairs:
        user_content = "Quiz items and attempts:\n\n" + "\n\n".join(pairs)
    else:
        user_content = (
            "No quiz items or attempts were submitted. "
            "Provide generic encouragement and a general study suggestion."
        )

    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
