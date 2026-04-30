#!/usr/bin/env bash
# PostToolUse hook for `git worktree add`: auto-create a uv venv and install deps.
#
# Triggered by the matching `if: "Bash(git worktree add *)"` rule in settings.json.
# PostToolUse on Bash only fires on success, so we know the worktree was created.
#
# Reads the standard Claude Code hook JSON from stdin and writes a JSON
# `hookSpecificOutput.additionalContext` block to stdout so Claude is told
# what happened (e.g. "venv created at <path>, installed N packages").

set -euo pipefail

# ---- helpers ----------------------------------------------------------------

emit_context() {
    # $1 = message string for Claude. Always exit 0 after this.
    jq -n --arg msg "$1" '{
        hookSpecificOutput: {
            hookEventName: "PostToolUse",
            additionalContext: $msg
        }
    }'
    exit 0
}

silent_exit() {
    # Nothing useful to report — exit 0 with no output so Claude sees nothing.
    exit 0
}

# ---- read input -------------------------------------------------------------

INPUT="$(cat)"
COMMAND="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""')"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // ""')"

if [ -z "$COMMAND" ]; then
    silent_exit
fi

# ---- parse the worktree path ------------------------------------------------
#
# Forms we want to handle:
#   git worktree add ../foo
#   git worktree add ../foo some-branch
#   git worktree add -b new-branch ../foo
#   git worktree add --detach ../foo HEAD~1
#   FOO=bar && git worktree add ../foo   (compound; last subcommand)
#
# Strategy: pull the segment that starts with `git worktree add` (the `if` rule
# guarantees one exists), then walk its args skipping option flags and their
# values to find the first positional, which is the path.

# Take the substring starting at the first `git worktree add` occurrence,
# then cut at the next shell separator (&&, ||, ;, |) so we only parse that
# subcommand's args.
SUB="${COMMAND#*git worktree add}"
SUB="${SUB%%&&*}"
SUB="${SUB%%||*}"
SUB="${SUB%%;*}"
SUB="${SUB%%|*}"

# Tokenize on whitespace. This is good enough for the common cases; paths with
# spaces in worktree adds are rare and would be quoted, in which case we fall
# back to silent_exit below if the directory check fails.
# shellcheck disable=SC2086
set -- $SUB

WORKTREE_PATH=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        # Flags that take a value — skip the next token.
        -b|-B|--reason|--orphan-branch)
            shift 2 || break
            ;;
        # Boolean flags — skip just this token.
        --detach|--checkout|--no-checkout|--lock|--no-track|--guess-remote|\
        --quiet|-q|--force|-f|--orphan)
            shift
            ;;
        # Long options with `=value` — skip just this token.
        --*=*)
            shift
            ;;
        # Anything else starting with `-` we don't recognize — skip defensively.
        -*)
            shift
            ;;
        # First positional is the path.
        *)
            WORKTREE_PATH="$1"
            break
            ;;
    esac
done

if [ -z "$WORKTREE_PATH" ]; then
    silent_exit
fi

# Resolve relative paths against the cwd Claude Code reported.
case "$WORKTREE_PATH" in
    /*) ABS_PATH="$WORKTREE_PATH" ;;
    *)  ABS_PATH="${CWD:-$PWD}/$WORKTREE_PATH" ;;
esac

# Normalize. If the path doesn't exist, the worktree add must have been a dry
# run or odd form we didn't parse — bail quietly.
if [ ! -d "$ABS_PATH" ]; then
    silent_exit
fi
ABS_PATH="$(cd "$ABS_PATH" && pwd)"

# ---- decide whether this is a Python project we should set up --------------

IS_PYTHON=0
for marker in pyproject.toml requirements.txt requirements.in setup.py setup.cfg; do
    if [ -f "$ABS_PATH/$marker" ]; then
        IS_PYTHON=1
        break
    fi
done

if [ "$IS_PYTHON" -eq 0 ]; then
    silent_exit
fi

# Don't clobber an existing venv (e.g. user already set one up, or worktree
# inherited one via a git hook).
if [ -d "$ABS_PATH/.venv" ]; then
    emit_context "Worktree at $ABS_PATH already has a .venv — skipped uv setup."
fi

# uv must be on PATH.
if ! command -v uv >/dev/null 2>&1; then
    emit_context "Worktree at $ABS_PATH looks like a Python project, but \`uv\` is not on PATH — skipped venv setup."
fi

# ---- create venv and install deps ------------------------------------------

LOG="$(mktemp)"
trap 'rm -f "$LOG"' EXIT

cd "$ABS_PATH"

if [ -f "pyproject.toml" ]; then
    # `uv sync` creates .venv and installs from pyproject/uv.lock in one step.
    if uv sync --all-extras >"$LOG" 2>&1; then
        SUMMARY="Created .venv and ran \`uv sync\` in $ABS_PATH (pyproject.toml detected)."
    else
        SUMMARY="Tried to set up venv at $ABS_PATH but \`uv sync\` failed:"$'\n'"$(tail -n 20 "$LOG")"
    fi
elif [ -f "requirements.txt" ]; then
    if uv venv >"$LOG" 2>&1 && uv pip install -r requirements.txt >>"$LOG" 2>&1; then
        SUMMARY="Created .venv at $ABS_PATH and installed requirements.txt with uv."
    else
        SUMMARY="Tried to set up venv at $ABS_PATH but uv venv / install failed:"$'\n'"$(tail -n 20 "$LOG")"
    fi
elif [ -f "requirements.in" ]; then
    if uv venv >"$LOG" 2>&1 && uv pip install -r requirements.in >>"$LOG" 2>&1; then
        SUMMARY="Created .venv at $ABS_PATH and installed requirements.in with uv."
    else
        SUMMARY="Tried to set up venv at $ABS_PATH but uv venv / install failed:"$'\n'"$(tail -n 20 "$LOG")"
    fi
else
    # setup.py / setup.cfg only — create the venv but don't guess at install args.
    if uv venv >"$LOG" 2>&1; then
        SUMMARY="Created .venv at $ABS_PATH with \`uv venv\` (legacy setup.py/cfg — no auto-install ran)."
    else
        SUMMARY="Tried to create venv at $ABS_PATH but \`uv venv\` failed:"$'\n'"$(tail -n 20 "$LOG")"
    fi
fi

emit_context "$SUMMARY"
