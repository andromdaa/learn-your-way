"""Prompt builder for the mnemonic generator."""

from __future__ import annotations

from lesson_graph.interfaces import ChatMessage
from lesson_graph.models import ConceptNode

_SYSTEM_PROMPT = (
    "You are an educational memory coach. Create a single memorable mnemonic "
    "for the key terms or concepts in the given concept summary. Choose the most "
    "appropriate device: an acronym, a rhyme, or a vivid association cue.\n\n"
    "Rules:\n"
    "  - The mnemonic must be directly inspired by terms in the summary.\n"
    "  - Keep it to one or two sentences maximum.\n"
    "  - Do not invent facts. The mnemonic may be creative, but must not contradict "
    "the concept.\n"
    "  - Return ONLY the mnemonic text — no preamble, no explanation."
)


def build_mnemonic_messages(concept: ConceptNode) -> list[ChatMessage]:
    """Build chat messages asking the model to create a mnemonic for a concept."""
    user_content = (
        f"Concept: {concept.title}\n"
        f"Learning objective: {concept.learning_objective}\n\n"
        f"Summary:\n{concept.summary}"
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
