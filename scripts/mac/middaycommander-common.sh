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
  : "${MIDDAY_RELEASE_REPO:=tungpastry/MiddayCommander}"
  : "${MIDDAY_RELEASES_ROOT:=/home/nexus/releases/middaycommander}"
  : "${MIDDAY_RELEASE_BINARY_NAME:=mdc}"
  : "${MIDDAY_RELEASE_SERVER_OS:=linux}"
  : "${MIDDAY_RELEASE_SERVER_ARCH:=amd64}"
  : "${MIDDAY_RELEASE_DIST_DIR:=${MIDDAY_MAC_ROOT}/dist}"
  : "${MIDDAY_RELEASE_STORAGE_DIR:=${MIDDAY_BRIDGE_MAC_ROOT}/storage/releases}"

  export MIDDAY_MAC_ROOT
  export MIDDAY_BRIDGE_MAC_ROOT
  export MIDDAY_ROUTER_BASE_URL
  export MIDDAY_DESKTOP_SSH
  export MIDDAY_SERVER_SSH
  export MIDDAY_SERVER_ROOT
  export MIDDAY_ROUTER_SERVICE
  export MIDDAY_DESKTOP_BRIDGE_ROOT
  export MIDDAY_REPORTS_DIR
  export MIDDAY_RELEASE_REPO
  export MIDDAY_RELEASES_ROOT
  export MIDDAY_RELEASE_BINARY_NAME
  export MIDDAY_RELEASE_SERVER_OS
  export MIDDAY_RELEASE_SERVER_ARCH
  export MIDDAY_RELEASE_DIST_DIR
  export MIDDAY_RELEASE_STORAGE_DIR
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

midday_now_utc_iso() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
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

midday_require_dir() {
  local dir="$1"
  local label="$2"
  if [[ ! -d "$dir" ]]; then
    echo "${label} not found: ${dir}" >&2
    exit 1
  fi
}

midday_require_clean_git_worktree() {
  local repo="$1"
  local status_output
  status_output="$(git -C "$repo" status --short)"
  if [[ -n "$status_output" ]]; then
    echo "Git worktree is not clean in ${repo}" >&2
    printf '%s\n' "$status_output" >&2
    exit 1
  fi
}

midday_require_annotated_tag_at_head() {
  local repo="$1"
  local tag="$2"
  local object_type
  local tag_commit
  local head_commit

  object_type="$(git -C "$repo" for-each-ref "refs/tags/${tag}" --format='%(objecttype)' | sed -n '1p')"
  if [[ -z "$object_type" ]]; then
    echo "Release tag not found locally: ${tag}" >&2
    exit 1
  fi
  if [[ "$object_type" != "tag" ]]; then
    echo "Release tag must be annotated: ${tag}" >&2
    exit 1
  fi

  tag_commit="$(git -C "$repo" rev-parse "${tag}^{commit}")"
  head_commit="$(git -C "$repo" rev-parse HEAD)"
  if [[ "$tag_commit" != "$head_commit" ]]; then
    echo "Release tag ${tag} must point to HEAD (${head_commit}), found ${tag_commit}" >&2
    exit 1
  fi

  printf '%s\n' "$tag_commit"
}

midday_release_dir_for_tag() {
  local tag="$1"
  printf '%s/releases/%s\n' "$MIDDAY_RELEASES_ROOT" "$tag"
}

midday_release_current_path() {
  printf '%s/current\n' "$MIDDAY_RELEASES_ROOT"
}

midday_local_release_dir_for_tag() {
  local tag="$1"
  printf '%s/%s\n' "$MIDDAY_RELEASE_STORAGE_DIR" "$tag"
}
