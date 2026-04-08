#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${1:-}" || -z "${2:-}" || -z "${3:-}" || -z "${4:-}" ]]; then
  echo "Usage: $0 <input-kind> <title> <repo> <context-file>" >&2
  exit 1
fi

INPUT_KIND="$1"
TITLE="$2"
REPO="$3"
CONTEXT_FILE="$4"
BASE_URL="${CODEX_BRIDGE_BASE_URL:-http://192.168.1.15:8787}"

if [[ ! -f "$CONTEXT_FILE" ]]; then
  echo "Context file not found: $CONTEXT_FILE" >&2
  exit 1
fi

jq -n \
  --arg title "$TITLE" \
  --arg input_kind "$INPUT_KIND" \
  --arg repo "$REPO" \
  --rawfile context "$CONTEXT_FILE" \
  '{title:$title, input_kind:$input_kind, repo:$repo, context:$context, source:"mac-dispatch", constraints:["Safe commands only for gemini automation."]}' \
  | curl -fsS "${BASE_URL}/v1/dispatch/task" \
      -H "Content-Type: application/json" \
      -d @- | jq .
