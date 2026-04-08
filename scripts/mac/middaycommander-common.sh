#!/usr/bin/env bash
set -euo pipefail

MIDDAY_COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIDDAY_BRIDGE_ROOT="$(cd "${MIDDAY_COMMON_DIR}/../.." && pwd)"

midday_source_env_if_present() {
  local file="$1"
  if [[ -f "$file" ]]; then
    set -a
    # shellcheck disable=SC1090
    . "$file"
    set +a
  fi
}

midday_load_env() {
  local defaults_file="${MIDDAY_TARGET_DEFAULTS_FILE:-${MIDDAY_BRIDGE_ROOT}/targets/middaycommander.env.example}"
  local override_file="${MIDDAY_TARGET_ENV_FILE:-${MIDDAY_BRIDGE_ROOT}/targets/middaycommander.env}"
  local repo_env_file="${CODEX_BRIDGE_ENV_FILE:-${MIDDAY_BRIDGE_ROOT}/.env}"

  # Precedence is defaults < target override < repo .env.
  midday_source_env_if_present "$defaults_file"
  midday_source_env_if_present "$override_file"
  midday_source_env_if_present "$repo_env_file"

  : "${MIDDAY_MAC_ROOT:=/Users/macadmin/Documents/New project/MiddayCommander}"
  : "${MIDDAY_BRIDGE_MAC_ROOT:=${CODEX_BRIDGE_MAC_ROOT:-${MIDDAY_BRIDGE_ROOT}}}"
  : "${MIDDAY_ROUTER_BASE_URL:=${CODEX_BRIDGE_BASE_URL:-http://192.168.1.15:8787}}"
  : "${MIDDAY_DESKTOP_SSH:=nexus@192.168.1.15}"
  : "${MIDDAY_SERVER_SSH:=nexus@192.168.1.30}"
  : "${MIDDAY_SERVER_ROOT:=/home/nexus/projects/MiddayCommander}"
  : "${MIDDAY_ROUTER_SERVICE:=codex-bridge.service}"
  : "${MIDDAY_DESKTOP_BRIDGE_ROOT:=/home/nexus/codex-bridge}"
  : "${MIDDAY_REPORTS_DIR:=${MIDDAY_BRIDGE_MAC_ROOT}/storage/reports}"

  export MIDDAY_MAC_ROOT
  export MIDDAY_BRIDGE_MAC_ROOT
  export MIDDAY_ROUTER_BASE_URL
  export MIDDAY_DESKTOP_SSH
  export MIDDAY_SERVER_SSH
  export MIDDAY_SERVER_ROOT
  export MIDDAY_ROUTER_SERVICE
  export MIDDAY_DESKTOP_BRIDGE_ROOT
  export MIDDAY_REPORTS_DIR
}

midday_require_cmd() {
  local cmd
  for cmd in "$@"; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      echo "Missing required command: $cmd" >&2
      exit 1
    fi
  done
}

midday_now_utc() {
  date -u +"%Y%m%dT%H%M%SZ"
}

midday_first_line() {
  printf '%s\n' "$1" | sed -n '1p'
}

midday_ssh_bash() {
  local host="$1"
  local command="$2"
  ssh "$host" "bash -lc $(printf '%q' "$command")"
}

midday_markdown_bool() {
  if [[ "$1" == "true" ]]; then
    printf 'yes'
  else
    printf 'no'
  fi
}
