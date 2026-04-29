#!/usr/bin/env python3
"""PreToolUse hook that blocks edits to the canonical lesson graph
schema unless explicitly enabled with SCHEMA_CHANGE=1 in the agent's
environment.

The schema (src/lesson_graph/models.py) is a hard-rule invariant per
AGENTS.md and docs/02-data-model.md. Schema changes must be
deliberate and accompanied by test updates in
tests/test_lesson_graph.py and, for semantically significant changes,
an ADR under docs/adr/.

The hook reads Claude Code's tool-use payload from stdin, extracts the
target file path from common keys (`file_path`, `path`), and blocks
the call if it targets the schema file without the override env var.

Exit codes follow the Claude Code hook protocol:
  0 -> allow
  2 -> block, show stderr message to the agent
"""

from __future__ import annotations

import json
import os
import sys

SCHEMA_PATH_SUFFIX = "src/lesson_graph/models.py"

# Bash commands that mutate files. If any of these tokens appear in a
# Bash command together with the schema path, the hook treats it as an
# edit to the schema. This is intentionally over-broad: false positives
# block a command and surface a clear message; false negatives let the
# schema be silently rewritten.
BASH_MUTATION_TOKENS = (
    "sed -i",
    "perl -i",
    "awk -i",
    "ed ",
    "patch ",
    "tee ",
    " > ",
    " >> ",
    "dd ",
    "truncate ",
    "rm ",
    "mv ",
    "cp ",
    "install ",
    "python -c",
    "python3 -c",
)

BLOCKED_MESSAGE = """\
Edit to src/lesson_graph/models.py blocked.

This file is the canonical lesson graph schema. Per AGENTS.md and
docs/02-data-model.md, schema changes must be intentional and paired
with:

  1. Test updates in tests/test_lesson_graph.py
  2. An ADR under docs/adr/ for semantically significant changes

To proceed, restart the session with SCHEMA_CHANGE=1 in the
environment, e.g.:

  SCHEMA_CHANGE=1 claude

If you reached this hook by accident, the change you wanted may
belong elsewhere (a new module, a generator, a validator).
"""


def _file_path_from_payload(payload: dict[str, object]) -> str:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    for key in ("file_path", "path"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return ""


def _bash_command_from_payload(payload: dict[str, object]) -> str:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    value = tool_input.get("command")
    return value if isinstance(value, str) else ""


def _bash_mutates_schema(command: str) -> bool:
    """Return True if `command` looks like it writes to the schema file.

    Conservative: returns True if the schema path appears in the
    command alongside any known mutation token. The point is not to
    perfectly parse shell — it is to make the obvious bypasses fail
    loudly. Edits that genuinely should not touch the schema have no
    reason to mention the path at all.
    """
    if SCHEMA_PATH_SUFFIX not in command:
        return False
    return any(token in command for token in BASH_MUTATION_TOKENS)


def _is_schema_target(payload: dict[str, object]) -> bool:
    """Return True if the payload targets the schema file via any tool.

    Covers both file-tool payloads (Edit/Write/MultiEdit, with
    `file_path` or `path`) and Bash payloads where the command looks
    like it mutates the schema.
    """
    file_path = _file_path_from_payload(payload)
    if file_path and file_path.endswith(SCHEMA_PATH_SUFFIX):
        return True

    command = _bash_command_from_payload(payload)
    return bool(command) and _bash_mutates_schema(command)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    if not isinstance(payload, dict):
        return 0

    if not _is_schema_target(payload):
        return 0

    if os.environ.get("SCHEMA_CHANGE") == "1":
        return 0

    sys.stderr.write(BLOCKED_MESSAGE)
    return 2


if __name__ == "__main__":
    sys.exit(main())
