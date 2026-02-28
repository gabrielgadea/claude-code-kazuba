#!/usr/bin/env bash
# PreCompact hook: save context checkpoint before compaction.
#
# Creates a checkpoint file with current session state so it can be
# recovered after compaction completes. Outputs rules/context to
# preserve via additionalContext JSON.
set -euo pipefail

# Read stdin (hook input JSON)
INPUT=$(cat)

# --- Checkpoint directory ---
CHECKPOINT_DIR="${HOME}/.claude/checkpoints"
mkdir -p "${CHECKPOINT_DIR}"

# Timestamp for checkpoint filename
TIMESTAMP=$(date -u '+%Y%m%d_%H%M%S')
CHECKPOINT_FILE="${CHECKPOINT_DIR}/pre_compact_${TIMESTAMP}.json"

# --- Gather state to preserve ---
CWD=$(pwd)
PROJECT_NAME=$(basename "${CWD}")
GIT_BRANCH="none"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
fi

# Write checkpoint file
python3 -c "
import json, sys
data = {
    'timestamp': '${TIMESTAMP}',
    'cwd': sys.argv[1],
    'project': sys.argv[2],
    'git_branch': sys.argv[3],
    'pre_compact': True,
}
with open(sys.argv[4], 'w') as f:
    json.dump(data, f, indent=2)
" "${CWD}" "${PROJECT_NAME}" "${GIT_BRANCH}" "${CHECKPOINT_FILE}"

# --- Output preserved rules ---
RULES="[auto-compact] Context checkpoint saved: ${CHECKPOINT_FILE}
Project: ${PROJECT_NAME} | Branch: ${GIT_BRANCH}
Restore critical context after compaction completes."

# Output JSON for Claude Code
python3 -c "
import json, sys
rules = sys.argv[1]
output = {
    'hookSpecificOutput': {
        'hookEventName': 'PreCompact',
        'additionalContext': rules,
    }
}
json.dump(output, sys.stdout)
" "${RULES}"
