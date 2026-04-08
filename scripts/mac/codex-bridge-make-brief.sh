#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${1:-}" || -z "${2:-}" || -z "${3:-}" ]]; then
  echo "Usage: $0 <title> <repo> <context-file>" >&2
  exit 1
fi

TITLE="$1"
REPO="$2"
CONTEXT_FILE="$3"
BASE_URL="${CODEX_BRIDGE_BASE_URL:-http://192.168.1.15:8787}"

if [[ ! -f "$CONTEXT_FILE" ]]; then
  echo "Context file not found: $CONTEXT_FILE" >&2
  exit 1
fi

jq -n \
  --arg title "$TITLE" \
  --arg repo "$REPO" \
  --rawfile context "$CONTEXT_FILE" \
  '{title:$title, repo:$repo, context:$context, constraints:["Keep changes practical and production-friendly."]}' \
  | curl -fsS "${BASE_URL}/v1/brief/codex" \
      -H "Content-Type: application/json" \
      -d @- | jq -r '.brief_markdown'
