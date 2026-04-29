from lesson_graph.models import ConceptNode, SourceSpan


def _format_span(span: SourceSpan) -> str:
    return (
        f"p{span.page_start}-p{span.page_end}  chars {span.char_start}-{span.char_end}"
    )


def _format_prereqs(prereqs: list[str]) -> str:
    return ", ".join(sorted(prereqs)) if prereqs else "(none)"


def _format_node(node: ConceptNode, connector: str, indent: str) -> str:
    spans_text = " | ".join(
        _format_span(s) for s in sorted(node.source_spans, key=lambda s: s.char_start)
    )
    lines = [
        f"{connector}[{node.id}] {node.title}",
        f"{indent}  Objective : {node.learning_objective}",
        f"{indent}  Spans     : {spans_text}",
        f"{indent}  Prereqs   : {_format_prereqs(node.prerequisites)}",
    ]
    return "\n".join(lines)


def render_concept_tree(nodes: list[ConceptNode]) -> str:
    sorted_nodes = sorted(nodes, key=lambda n: n.id)
    header = f"Concepts ({len(sorted_nodes)})"
    if not sorted_nodes:
        return header + "\n"

    parts = [header]
    for i, node in enumerate(sorted_nodes):
        is_last = i == len(sorted_nodes) - 1
        connector = "└── " if is_last else "├── "
        indent = "    " if is_last else "│   "
        parts.append(_format_node(node, connector, indent))

    return "\n".join(parts) + "\n"
