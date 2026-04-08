#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

load_env_value() {
  local key="$1"
  local line=""
  local value=""

  [[ -f "$ENV_FILE" ]] || return 1

  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    [[ "${line#\#}" == "$line" ]] || continue
    if [[ "$line" == "${key}="* ]]; then
      value="${line#*=}"
      if [[ "${value}" == \"*\" && "${value}" == *\" ]]; then
        value="${value:1:-1}"
      fi
      printf '%s' "$value"
      return 0
    fi
  done <"$ENV_FILE"

  return 1
}

if [[ -z "${CODEX_BRIDGE_PUSH_SSH_ALIAS:-}" ]]; then
  CODEX_BRIDGE_PUSH_SSH_ALIAS="$(load_env_value CODEX_BRIDGE_PUSH_SSH_ALIAS || true)"
fi

if [[ -z "${CODEX_BRIDGE_MAC_ROOT:-}" ]]; then
  CODEX_BRIDGE_MAC_ROOT="$(load_env_value CODEX_BRIDGE_MAC_ROOT || true)"
fi

if [[ "${1:-}" != "--job-file" || -z "${2:-}" ]]; then
  echo "Usage: $0 --job-file <gemini-job.json>" >&2
  exit 1
fi

JOB_FILE="$2"
PUSH_ALIAS="${CODEX_BRIDGE_PUSH_SSH_ALIAS:-MacMiniGemini}"
REMOTE_ROOT="${CODEX_BRIDGE_MAC_ROOT:-$HOME/codex-bridge}"

if [[ ! -f "$JOB_FILE" ]]; then
  echo "Job file not found: $JOB_FILE" >&2
  exit 1
fi

ssh "$PUSH_ALIAS" "cd '$REMOTE_ROOT' && ./scripts/mac/codex-bridge-run-gemini.sh --stdin-json" <"$JOB_FILE"
