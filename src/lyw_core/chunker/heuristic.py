import hashlib
import re

from lesson_graph.models import ConceptNode, SourceSpan
from lyw_core.parser.models import ParsedBlock, ParsedDocument

_HEADING_TYPES: frozenset[str] = frozenset({"section_header", "title"})
_MAX_TITLE_FALLBACK = 50

# Headings used by textbooks as structural chrome rather than as
# pedagogical units. Matched case-insensitively against the heading text.
# Patterns are intentionally tight to avoid swallowing legitimate concepts
# that happen to share a word ("Analysis of variance" vs. just "Analysis").
_SCAFFOLDING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^solution\s*\d*\s*$", re.IGNORECASE),
    re.compile(r"^analysis\s*\d*\s*$", re.IGNORECASE),
    re.compile(r"^example\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^try\s+it\s*#?\s*\d*\s*$", re.IGNORECASE),
    re.compile(r"^learning\s+objectives?\s*$", re.IGNORECASE),
    re.compile(r"^media\s*$", re.IGNORECASE),
    re.compile(r"^verbal\s*$", re.IGNORECASE),
    re.compile(r"^real[- ]world\s+applications?\s*$", re.IGNORECASE),
    re.compile(r"^extensions?\s*$", re.IGNORECASE),
    re.compile(r"^chapter\s+review\s*$", re.IGNORECASE),
    re.compile(r"^key\s+(terms|equations|concepts)\s*$", re.IGNORECASE),
    re.compile(r"^practice\s+test\s*$", re.IGNORECASE),
    re.compile(r"^exercises?\s*$", re.IGNORECASE),
    re.compile(r"^review\s+exercises?\s*$", re.IGNORECASE),
)

# Minimum total character span of body blocks for a heading-bounded
# section to qualify as a standalone concept. Heading-only sections
# (a chapter cover or table-of-contents header) fall below this floor
# and are merged into their predecessor. Threshold tuned to allow a
# one-paragraph definition (~120 chars) through.
_MIN_BODY_CHARS = 120


def _make_id(doc_id: str, char_start: int, char_end: int) -> str:
    key = f"{doc_id}::{char_start}:{char_end}"
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def _is_scaffolding_heading(block: ParsedBlock) -> bool:
    """Return True if the heading text matches any scaffolding pattern."""
    text = block.text.strip()
    return any(p.match(text) for p in _SCAFFOLDING_PATTERNS)


def _section_body_chars(section: list[ParsedBlock]) -> int:
    """Total character span covered by a section's body blocks (excluding heading)."""
    if not section:
        return 0
    body = section[1:] if section[0].block_type in _HEADING_TYPES else section
    return sum(b.char_end - b.char_start for b in body)


def _truncate_title(text: str) -> str:
    """Truncate body-fallback title at the last word boundary within the
    first ``_MAX_TITLE_FALLBACK`` characters, appending an ellipsis.

    Returns ``text`` verbatim when it already fits within the limit.  When
    the prefix contains no whitespace at all (e.g. a long URL) we fall
    back to a hard slice plus ellipsis so the truncation is at least
    visually explicit.
    """
    if len(text) <= _MAX_TITLE_FALLBACK:
        return text
    for i in range(_MAX_TITLE_FALLBACK - 1, 0, -1):
        if text[i].isspace():
            return text[:i].rstrip() + "…"
    return text[:_MAX_TITLE_FALLBACK].rstrip() + "…"


class HeuristicChunker:
    """Deterministic first-pass chunker: splits a ParsedDocument into
    ConceptNodes at heading boundaries with a max-chars fallback.

    Each produced node records provenance="heuristic" so T9's LLM
    refiner can distinguish its own output from this stage.
    """

    def __init__(self, doc_id: str, max_chars: int = 2000) -> None:
        self._doc_id = doc_id
        self._max_chars = max_chars

    def chunk(self, doc: ParsedDocument) -> list[ConceptNode]:
        sections = self._split_into_sections(doc.blocks)
        sections = self._merge_scaffolding(sections)
        nodes: list[ConceptNode] = []
        for section in sections:
            nodes.extend(self._section_to_nodes(section))
        # Wire a linear prerequisite chain based on document order.  The first
        # concept has no prerequisites; each subsequent concept lists its
        # immediate predecessor as its sole prerequisite.
        for i in range(1, len(nodes)):
            nodes[i] = nodes[i].model_copy(update={"prerequisites": [nodes[i - 1].id]})
        return nodes

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _split_into_sections(
        self, blocks: list[ParsedBlock]
    ) -> list[list[ParsedBlock]]:
        """Group consecutive blocks into heading-bounded sections."""
        sections: list[list[ParsedBlock]] = []
        current: list[ParsedBlock] = []
        for block in blocks:
            if block.block_type in _HEADING_TYPES and current:
                sections.append(current)
                current = [block]
            else:
                current.append(block)
        if current:
            sections.append(current)
        return sections

    def _merge_scaffolding(
        self, sections: list[list[ParsedBlock]]
    ) -> list[list[ParsedBlock]]:
        """Fold scaffolding-shaped or thin-body sections into their predecessor.

        A section is merged into the preceding section's block list if:
          - its leading heading matches a ``_SCAFFOLDING_PATTERNS`` entry, OR
          - its body content totals fewer than ``_MIN_BODY_CHARS`` characters.

        The merged heading is preserved as a body block so its text remains in
        the source span and continues to feed the parent's ``summary`` join.

        The first section is always retained: with no parent to merge into,
        dropping or absorbing it would lose its body. A document that opens
        with a scaffolding heading is pathological and is accepted as-is.
        """
        if not sections:
            return sections

        merged: list[list[ParsedBlock]] = [sections[0]]
        for section in sections[1:]:
            if not section:
                continue
            heading = section[0] if section[0].block_type in _HEADING_TYPES else None
            is_scaffolding = heading is not None and _is_scaffolding_heading(heading)
            is_thin_body = _section_body_chars(section) < _MIN_BODY_CHARS
            if is_scaffolding or is_thin_body:
                merged[-1].extend(section)
            else:
                merged.append(section)
        return merged

    def _section_to_nodes(self, section: list[ParsedBlock]) -> list[ConceptNode]:
        if not section:
            return []
        heading = section[0] if section[0].block_type in _HEADING_TYPES else None
        body_blocks = section[1:] if heading else section[:]
        sub_groups = self._split_body(heading, body_blocks)
        return [self._make_node(h, body) for h, body in sub_groups]

    def _split_body(
        self,
        heading: ParsedBlock | None,
        body_blocks: list[ParsedBlock],
    ) -> list[tuple[ParsedBlock | None, list[ParsedBlock]]]:
        """Split body_blocks into groups each fitting within max_chars.

        The heading is attached only to the first group; subsequent
        groups are headingless so they generate distinct IDs and titles.
        """
        if not body_blocks:
            return [(heading, [])]

        heading_chars = (heading.char_end - heading.char_start) if heading else 0
        result: list[tuple[ParsedBlock | None, list[ParsedBlock]]] = []
        current: list[ParsedBlock] = []
        current_chars = heading_chars
        is_first = True

        for block in body_blocks:
            block_chars = block.char_end - block.char_start
            # +1 for the newline separator between blocks
            separator = 1 if current else 0
            if current and current_chars + separator + block_chars > self._max_chars:
                result.append((heading if is_first else None, current))
                current = [block]
                current_chars = block_chars
                is_first = False
            else:
                current_chars += separator + block_chars
                current.append(block)

        if current:
            result.append((heading if is_first else None, current))

        return result

    def _make_node(
        self,
        heading: ParsedBlock | None,
        body_blocks: list[ParsedBlock],
    ) -> ConceptNode:
        all_blocks: list[ParsedBlock] = ([heading] if heading else []) + body_blocks

        if heading:
            title = heading.text
        elif body_blocks:
            title = _truncate_title(body_blocks[0].text)
        else:
            title = "Untitled"

        summary = " ".join(b.text for b in body_blocks) or title
        learning_objective = f"Understand {title}"

        char_start = all_blocks[0].char_start
        char_end = all_blocks[-1].char_end
        page_start = all_blocks[0].page_number
        page_end = all_blocks[-1].page_number

        return ConceptNode(
            id=_make_id(self._doc_id, char_start, char_end),
            title=title,
            summary=summary,
            learning_objective=learning_objective,
            source_spans=[
                SourceSpan(
                    doc_id=self._doc_id,
                    page_start=page_start,
                    page_end=page_end,
                    char_start=char_start,
                    char_end=char_end,
                )
            ],
            prerequisites=[],
            provenance="heuristic",
        )
