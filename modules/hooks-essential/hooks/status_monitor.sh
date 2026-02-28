#!/usr/bin/env bash
# SessionStart hook: report session environment info.
#
# Outputs a JSON additionalContext with session diagnostics:
# - Python version
# - Git branch and status
# - Project name
# - Pending TODO count
# - Timestamp
set -euo pipefail

# Read stdin (hook input JSON) — we mostly ignore it but consume it
INPUT=$(cat)

# --- Gather session info ---

# Python version
PYTHON_VERSION=$(python3 --version 2>/dev/null | awk '{print $2}' || echo "unknown")

# Git branch
GIT_BRANCH="(not a git repo)"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
fi

# Git dirty status
GIT_DIRTY="clean"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        GIT_DIRTY="dirty"
    fi
fi

# Project name (directory name)
PROJECT_NAME=$(basename "$(pwd)")

# Pending TODOs — count TODO/FIXME/HACK/XXX in source files
TODO_COUNT=0
if command -v rg >/dev/null 2>&1; then
    TODO_COUNT=$(rg -c 'TODO|FIXME|HACK|XXX' --type py --type sh --type js --type ts 2>/dev/null | awk -F: '{s+=$2} END {print s+0}' || echo "0")
elif command -v grep >/dev/null 2>&1; then
    TODO_COUNT=$(grep -r -c 'TODO\|FIXME\|HACK\|XXX' --include='*.py' --include='*.sh' --include='*.js' --include='*.ts' . 2>/dev/null | awk -F: '{s+=$2} END {print s+0}' || echo "0")
fi

# Timestamp
TIMESTAMP=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

# --- Build context message ---
CONTEXT="[status-monitor] Session started at ${TIMESTAMP}
Python: ${PYTHON_VERSION} | Git: ${GIT_BRANCH} (${GIT_DIRTY}) | Project: ${PROJECT_NAME}
Pending TODOs: ${TODO_COUNT}"

# --- Output JSON ---
# Use python3 for safe JSON encoding
python3 -c "
import json, sys
ctx = sys.argv[1]
output = {
    'hookSpecificOutput': {
        'hookEventName': 'SessionStart',
        'additionalContext': ctx,
    }
}
json.dump(output, sys.stdout)
" "${CONTEXT}"
