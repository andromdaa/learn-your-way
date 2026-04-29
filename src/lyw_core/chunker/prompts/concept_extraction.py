"""Prompt templates for the LLM concept-extraction step."""

SYSTEM: str = (
    "You are an educational content structuring assistant. "
    "Given a passage of text, extract structured concept metadata. "
    "Respond with a single JSON object and nothing else — no markdown fences, "
    "no explanation, no trailing text."
)

USER_TEMPLATE: str = """\
Extract concept metadata from the following educational passage.

CONCEPT TITLE: {title}

TEXT:
{text}

Respond with exactly this JSON structure (no markdown, no extra keys):
{{
  "title": "<concise concept title>",
  "summary": "<2-3 sentence summary of the concept>",
  "learning_objective": "<one measurable learning objective starting with a verb>",
  "prerequisites": ["<prerequisite concept title>", ...]
}}"""
