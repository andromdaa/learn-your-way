#!/usr/bin/env bash
set -euo pipefail

PHASE="${1:-snapshot}"

# Only run inside a git repo.
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# Avoid committing during rebases/merges/etc.
GIT_DIR="$(git rev-parse --git-dir)"
if [[ -d "$GIT_DIR/rebase-merge" || -d "$GIT_DIR/rebase-apply" || -f "$GIT_DIR/MERGE_HEAD" || -f "$GIT_DIR/CHERRY_PICK_HEAD" ]]; then
  echo "Skipping Claude auto-commit: repo is in the middle of a Git operation." >&2
  exit 0
fi

# Avoid nested or repeated hook behavior.
export CLAUDE_AUTOCOMMIT_RUNNING=1

# Stage everything, including deletions and untracked files.
git add -A

# If nothing changed, do nothing.
if git diff --cached --quiet; then
  exit 0
fi

TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

git commit -m "claude: ${PHASE} snapshot ${TIMESTAMP}" >/dev/null