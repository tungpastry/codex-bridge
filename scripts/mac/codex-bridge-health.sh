#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${CODEX_BRIDGE_BASE_URL:-http://192.168.1.15:8787}"
curl -fsS "${BASE_URL}/health" | jq .
