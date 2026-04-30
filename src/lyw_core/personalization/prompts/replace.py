"""Prompt builder for the example-replacement generator.

A "personalizable segment" is conservatively scoped: only explicit
analogies ("like a ..."), illustrative scenarios ("imagine ..."), and
flavor-text examples may be rewritten. Definitions, equations, named
theorems, formal proofs, and any sentence containing canonical
terminology are NEVER rewritten — over-restriction is safer than
over-permissiveness for source fidelity (see T7 risk notes).
"""

from __future__ import annotations

from lesson_graph.interfaces import ChatMessage
from lesson_graph.models import ConceptNode
from lyw_core.profiles.models import LearnerProfile

_SYSTEM_PROMPT = (
    "You are an educational text editor specializing in personalization. "
    "Your job is to find personalizable segments in a concept summary and "
    "rewrite them to connect with the learner's interests.\n\n"
    "Personalizable segments are EXCLUSIVELY:\n"
    "  - Explicit analogies (phrases like 'like a ...', 'similar to ...').\n"
    "  - Illustrative scenarios ('imagine ...', 'consider a ...', 'for example ...').\n"
    "  - Flavor-text examples that illustrate but do not define a concept.\n\n"
    "NEVER rewrite:\n"
    "  - Definitions, formulas, equations, named theorems, or proofs.\n"
    "  - Sentences containing canonical terminology.\n"
    "  - Numeric facts, dates, or named entities core to the concept.\n\n"
    "Return a JSON array (and ONLY a JSON array, no preamble) where each "
    "element is an object with these exact keys:\n"
    '  "original_text": the exact substring from the summary being replaced,\n'
    '  "replacement_text": the rewritten segment using the chosen interest,\n'
    '  "interest": the single learner interest used for this replacement.\n\n'
    "If no segments are personalizable, return an empty array: []"
)


def build_replace_messages(
    concept: ConceptNode, profile: LearnerProfile
) -> list[ChatMessage]:
    """Build chat messages instructing the model to propose interest-linked replacements."""
    interests_str = ", ".join(profile.interests) if profile.interests else "(none)"
    user_content = (
        f"Learner interests: {interests_str}\n"
        f"Grade level: {profile.grade_level}\n\n"
        f"Concept summary:\n{concept.summary}"
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
