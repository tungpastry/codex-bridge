#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${CODEX_BRIDGE_BASE_URL:-http://192.168.1.15:8787}"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <input-file>|<inline-item-1> [inline-item-2 ...]" >&2
  exit 1
fi

if [[ -f "${1:-}" ]]; then
  jq -n --rawfile raw_text "$1" '{raw_text:$raw_text, source:"mac-script"}' \
    | curl -fsS "${BASE_URL}/v1/report/daily" \
        -H "Content-Type: application/json" \
        -d @- | jq -r '.markdown'
else
  jq -n --args "$@" '$ARGS.positional | {items: ., source:"mac-script"}' \
    | curl -fsS "${BASE_URL}/v1/report/daily" \
        -H "Content-Type: application/json" \
        -d @- | jq -r '.markdown'
fi
