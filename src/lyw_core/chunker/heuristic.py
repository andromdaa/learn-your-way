import hashlib

from lesson_graph.models import ConceptNode, SourceSpan
from lyw_core.parser.models import ParsedBlock, ParsedDocument

_HEADING_TYPES: frozenset[str] = frozenset({"section_header", "title"})
_MAX_TITLE_FALLBACK = 50


def _make_id(doc_id: str, char_start: int, char_end: int) -> str:
    key = f"{doc_id}::{char_start}:{char_end}"
    return hashlib.sha1(key.encode()).hexdigest()[:12]


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
        nodes: list[ConceptNode] = []
        for section in sections:
            nodes.extend(self._section_to_nodes(section))
        # Wire a linear prerequisite chain based on document order so that
        # MindMapGenerator BFS can traverse the full concept graph.  The first
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
            title = body_blocks[0].text[:_MAX_TITLE_FALLBACK]
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
