"""Tests for the schema-guard PreToolUse hook.

The hook (.claude/hooks/guard-schema.py) blocks edits to the canonical
lesson graph schema unless SCHEMA_CHANGE=1 is set. This file is the
regression test for that behavior. It invokes the hook as a
subprocess, the same way Claude Code does, and asserts the documented
exit-code contract.

Contract under test:
    exit 0  -> allow the tool call
    exit 2  -> block; stderr is shown to the agent

The hook is code. CI must run these tests so a refactor that breaks
the contract fails the build.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK = REPO_ROOT / ".claude" / "hooks" / "guard-schema.py"


def _run(
    payload: object, *, schema_change: bool = False
) -> subprocess.CompletedProcess[str]:
    """Invoke the hook with the given JSON payload on stdin.

    Mirrors how Claude Code invokes PreToolUse hooks: a single JSON
    object on stdin, environment inherited from the agent process.
    """
    env = os.environ.copy()
    env.pop("SCHEMA_CHANGE", None)
    if schema_change:
        env["SCHEMA_CHANGE"] = "1"
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_hook_is_executable() -> None:
    assert HOOK.is_file(), f"hook missing at {HOOK}"
    assert os.access(HOOK, os.X_OK), "hook must be executable"


def test_blocks_edit_to_schema_relative_path() -> None:
    result = _run({"tool_input": {"file_path": "src/lesson_graph/models.py"}})
    assert result.returncode == 2
    assert "blocked" in result.stderr.lower()


def test_blocks_edit_to_schema_absolute_path() -> None:
    abs_path = str(REPO_ROOT / "src" / "lesson_graph" / "models.py")
    result = _run({"tool_input": {"file_path": abs_path}})
    assert result.returncode == 2


def test_allows_edit_when_schema_change_env_set() -> None:
    result = _run(
        {"tool_input": {"file_path": "src/lesson_graph/models.py"}},
        schema_change=True,
    )
    assert result.returncode == 0
    assert result.stderr == ""


def test_allows_edit_to_unrelated_file() -> None:
    result = _run({"tool_input": {"file_path": "src/lesson_graph/other.py"}})
    assert result.returncode == 0


def test_allows_edit_to_models_in_unrelated_package() -> None:
    """Suffix match must not catch a different package's models.py."""
    result = _run({"tool_input": {"file_path": "src/some_other_pkg/models.py"}})
    assert result.returncode == 0


def test_accepts_path_key_alternative() -> None:
    """Some tools use `path` instead of `file_path`."""
    result = _run({"tool_input": {"path": "src/lesson_graph/models.py"}})
    assert result.returncode == 2


def test_ignores_payload_with_no_path() -> None:
    result = _run({"tool_input": {"command": "ls"}})
    assert result.returncode == 0


def test_ignores_malformed_json() -> None:
    """Hook must not block on parser errors; that would deadlock the agent."""
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input="not json at all",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0


def test_ignores_payload_that_is_not_an_object() -> None:
    result = _run(["unexpected", "list", "payload"])
    assert result.returncode == 0


def test_schema_change_must_equal_exactly_one() -> None:
    """Truthy-but-not-'1' must NOT bypass the guard.

    Pin the exact-match contract so a future refactor doesn't loosen
    it to truthy-string semantics.
    """
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_input": {"file_path": "src/lesson_graph/models.py"}}),
        capture_output=True,
        text=True,
        env={**os.environ, "SCHEMA_CHANGE": "true"},
        check=False,
    )
    assert result.returncode == 2


# Bash payloads ------------------------------------------------------------


def test_blocks_bash_redirection_to_schema() -> None:
    result = _run(
        {"tool_input": {"command": "cat new.py > src/lesson_graph/models.py"}}
    )
    assert result.returncode == 2


def test_blocks_bash_sed_in_place_on_schema() -> None:
    result = _run(
        {"tool_input": {"command": "sed -i 's/foo/bar/' src/lesson_graph/models.py"}}
    )
    assert result.returncode == 2


def test_blocks_bash_append_redirection_to_schema() -> None:
    result = _run({"tool_input": {"command": "echo x >> src/lesson_graph/models.py"}})
    assert result.returncode == 2


def test_blocks_bash_rm_of_schema() -> None:
    result = _run({"tool_input": {"command": "rm src/lesson_graph/models.py"}})
    assert result.returncode == 2


def test_blocks_bash_mv_overwriting_schema() -> None:
    result = _run(
        {"tool_input": {"command": "mv /tmp/new.py src/lesson_graph/models.py"}}
    )
    assert result.returncode == 2


def test_allows_bash_read_only_on_schema() -> None:
    """Reading the schema is fine. Only mutating commands are blocked."""
    result = _run({"tool_input": {"command": "cat src/lesson_graph/models.py"}})
    assert result.returncode == 0


def test_allows_bash_grep_on_schema() -> None:
    result = _run(
        {"tool_input": {"command": "grep -n SourceSpan src/lesson_graph/models.py"}}
    )
    assert result.returncode == 0


def test_allows_bash_unrelated_redirection() -> None:
    result = _run({"tool_input": {"command": "echo hello > /tmp/x.txt"}})
    assert result.returncode == 0


def test_allows_bash_sed_with_schema_change_env() -> None:
    result = _run(
        {"tool_input": {"command": "sed -i 's/x/y/' src/lesson_graph/models.py"}},
        schema_change=True,
    )
    assert result.returncode == 0


@pytest.mark.parametrize(
    "value",
    ["", "0", "false", "no"],
)
def test_falsy_schema_change_values_still_block(value: str) -> None:
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_input": {"file_path": "src/lesson_graph/models.py"}}),
        capture_output=True,
        text=True,
        env={**os.environ, "SCHEMA_CHANGE": value},
        check=False,
    )
    assert result.returncode == 2
