"""Prompt builder for the embedded MCQ generator.

Instructs the model to emit between one and three multiple-choice
questions for a single ConceptNode. Each MCQ has exactly four options
(one correct), a non-empty rationale, a Bloom's-level tag, and a
difficulty label. Items missing correct_answer or bloom_level are
discarded by the generator.
"""

from __future__ import annotations

from lesson_graph.interfaces import ChatMessage
from lesson_graph.models import ConceptNode

_SYSTEM_PROMPT = (
    "You are an assessment author. Produce between one and three "
    "multiple-choice questions that assess the given concept's learning "
    "objective. Every question MUST be answerable from the concept summary "
    "alone — never invent facts that do not appear in it.\n\n"
    "Each question MUST have exactly four options, exactly one of which is "
    "correct. The correct_answer field MUST be the correct option's text "
    "verbatim (a substring match against one of the four options).\n\n"
    "Bloom's level MUST be one of: 'remember', 'understand', 'apply', "
    "'analyze', 'evaluate', 'create'. Difficulty MUST be one of: 'easy', "
    "'medium', 'hard'.\n\n"
    "Return a JSON array (and ONLY a JSON array, no preamble, no trailing "
    "text) where each element is an object with these exact keys:\n"
    '  "prompt": the question text,\n'
    '  "options": a list of exactly four option strings,\n'
    '  "correct_answer": the correct option text (verbatim from options),\n'
    '  "rationale": a short explanation of why the answer is correct,\n'
    '  "bloom_level": one of the six Bloom\'s values above,\n'
    '  "difficulty": one of "easy", "medium", "hard".\n\n'
    "If the concept cannot support a faithful question, return: []"
)


def build_mcq_messages(concept: ConceptNode) -> list[ChatMessage]:
    """Build chat messages instructing the model to author MCQs for a concept."""
    user_content = (
        f"Concept title: {concept.title}\n"
        f"Learning objective: {concept.learning_objective}\n\n"
        f"Concept summary:\n{concept.summary}"
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
