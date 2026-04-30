"""Unit tests for MindMapValidator."""

from __future__ import annotations

from lyw_core.validators.mindmap import MindMapValidator


def _valid_mermaid() -> str:
    return (
        "flowchart TD\n"
        '    c1["Roots"]\n'
        '    c2["Stems"]\n'
        "    c1 --> c2\n"
    )


def test_valid_mermaid_passes() -> None:
    result = MindMapValidator().validate(_valid_mermaid())
    assert result.passed is True
    assert result.reason is None


def test_graph_lr_preamble_passes() -> None:
    payload = 'graph LR\n    a["Alpha"]\n    b["Beta"]\n    a --> b\n'
    result = MindMapValidator().validate(payload)
    assert result.passed is True


def test_empty_string_fails() -> None:
    result = MindMapValidator().validate("")
    assert result.passed is False
    assert result.reason is not None
    assert "empty" in result.reason


def test_whitespace_only_fails() -> None:
    result = MindMapValidator().validate("   \n\n  ")
    assert result.passed is False


def test_single_node_fails() -> None:
    payload = 'flowchart TD\n    c1["Only"]\n'
    result = MindMapValidator().validate(payload)
    assert result.passed is False
    reason = result.reason or ""
    assert "2 nodes" in reason


def test_missing_preamble_fails() -> None:
    payload = '    c1["Roots"]\n    c2["Stems"]\n    c1 --> c2\n'
    result = MindMapValidator().validate(payload)
    assert result.passed is False
    reason = result.reason or ""
    assert "preamble" in reason


def test_wrong_preamble_keyword_fails() -> None:
    payload = 'pie\n    c1["x"]\n    c2["y"]\n'
    result = MindMapValidator().validate(payload)
    assert result.passed is False


def test_empty_node_label_fails() -> None:
    payload = "flowchart TD\n" '    c1[""]\n' '    c2["Stems"]\n' "    c1 --> c2\n"
    result = MindMapValidator().validate(payload)
    assert result.passed is False
    reason = result.reason or ""
    assert "empty node label" in reason
