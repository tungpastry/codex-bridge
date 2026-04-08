#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/mac/middaycommander-common.sh
source "${SCRIPT_DIR}/middaycommander-common.sh"

usage() {
  cat <<'EOF'
Usage: middaycommander-release.sh --tag <tag> [--dry-run] [--prepare-only | --publish-only | --promote-only] [--help]

Build, publish, and promote a MiddayCommander release from the Mac mini through
codex-bridge.
EOF
}

fail() {
  echo "$1" >&2
  exit 1
}

MODE="full"
DRY_RUN=0
TAG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag)
      [[ $# -ge 2 ]] || fail "Missing value for --tag"
      TAG="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --prepare-only)
      MODE="prepare-only"
      shift
      ;;
    --publish-only)
      MODE="publish-only"
      shift
      ;;
    --promote-only)
      MODE="promote-only"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 1
      ;;
  esac
done

[[ -n "$TAG" ]] || fail "Release tag is required. Usage: middaycommander-release.sh --tag <tag>"

midday_load_env

PROJECT_NAME="$(basename "$MIDDAY_MAC_ROOT")"
RELEASE_DIR="$(midday_local_release_dir_for_tag "$TAG")"
RELEASE_ASSETS_DIR="${RELEASE_DIR}/assets"
SUMMARY_FILE="${RELEASE_DIR}/summary.json"
PUBLISH_FILE="${RELEASE_DIR}/publish.json"
PROMOTE_FILE="${RELEASE_DIR}/promote.json"
SERVER_RELEASE_DIR="$(midday_release_dir_for_tag "$TAG")"
SERVER_CURRENT_PATH="$(midday_release_current_path)"
SERVER_RELEASE_REL="releases/${TAG}"
SERVER_TARGET_ARCHIVE="${PROJECT_NAME}_${TAG}_${MIDDAY_RELEASE_SERVER_OS}_${MIDDAY_RELEASE_SERVER_ARCH}.tar.gz"

release_asset_names_json() {
  local asset
  for asset in "${RELEASE_ASSET_NAMES[@]}"; do
    printf '%s\n' "$asset"
  done | jq -R . | jq -s .
}

read_summary_field() {
  local filter="$1"
  jq -r "$filter" "$SUMMARY_FILE"
}

prepare_release() {
  local source_commit="$1"
  local prepared_at
  local checksums_path
  local asset_names_json
  local build_dir
  local temp_root
  local stage_dir
  local parsed
  local os_name
  local arch_name
  local binary_path
  local archive_name
  local archive_path
  local release_assets_glob

  rm -rf "$RELEASE_DIR"
  mkdir -p "$RELEASE_ASSETS_DIR"

  (
    cd "$MIDDAY_MAC_ROOT"
    go test ./...
    go build ./...
    goreleaser build --clean
  )

  RELEASE_ASSET_NAMES=()

  while IFS= read -r build_dir; do
    parsed="$(parse_build_dir "$build_dir")" || continue
    os_name="${parsed%% *}"
    arch_name="${parsed##* }"
    binary_path="${build_dir}/${MIDDAY_RELEASE_BINARY_NAME}"
    if [[ "$os_name" == "windows" ]]; then
      binary_path="${build_dir}/${MIDDAY_RELEASE_BINARY_NAME}.exe"
    fi
    [[ -f "$binary_path" ]] || continue

    archive_name="${PROJECT_NAME}_${TAG}_${os_name}_${arch_name}.tar.gz"
    archive_path="${RELEASE_ASSETS_DIR}/${archive_name}"
    temp_root="$(mktemp -d "${TMPDIR:-/tmp}/midday-release.XXXXXX")"
    stage_dir="${temp_root}/stage"
    mkdir -p "$stage_dir"
    cp "$binary_path" "$stage_dir/"
    if [[ -f "${MIDDAY_MAC_ROOT}/LICENSE" ]]; then
      cp "${MIDDAY_MAC_ROOT}/LICENSE" "$stage_dir/"
    fi
    if [[ -f "${MIDDAY_MAC_ROOT}/README.md" ]]; then
      cp "${MIDDAY_MAC_ROOT}/README.md" "$stage_dir/"
    fi
    tar -C "$stage_dir" -czf "$archive_path" .
    rm -rf "$temp_root"
    RELEASE_ASSET_NAMES+=("$archive_name")
  done < <(find "$MIDDAY_RELEASE_DIST_DIR" -mindepth 1 -maxdepth 1 -type d | sort)

  [[ "${#RELEASE_ASSET_NAMES[@]}" -gt 0 ]] || fail "No release archives were created from ${MIDDAY_RELEASE_DIST_DIR}"

  if [[ ! -f "${RELEASE_ASSETS_DIR}/${SERVER_TARGET_ARCHIVE}" ]]; then
    fail "Required server artifact not found after packaging: ${SERVER_TARGET_ARCHIVE}"
  fi

  checksums_path="${RELEASE_ASSETS_DIR}/checksums.txt"
  (
    cd "$RELEASE_ASSETS_DIR"
    shasum -a 256 ./*.tar.gz | awk '{print $1 "  " $2}' > "$checksums_path"
  )

  prepared_at="$(midday_now_utc_iso)"
  asset_names_json="$(release_asset_names_json)"
  jq -n \
    --arg tag "$TAG" \
    --arg repo_root "$MIDDAY_MAC_ROOT" \
    --arg source_commit "$source_commit" \
    --arg prepared_at "$prepared_at" \
    --arg release_repo "$MIDDAY_RELEASE_REPO" \
    --arg dist_dir "$MIDDAY_RELEASE_DIST_DIR" \
    --arg server_os "$MIDDAY_RELEASE_SERVER_OS" \
    --arg server_arch "$MIDDAY_RELEASE_SERVER_ARCH" \
    --arg server_archive "$SERVER_TARGET_ARCHIVE" \
    --arg checksums "checksums.txt" \
    --argjson asset_names "$asset_names_json" \
    '{
      tag: $tag,
      repo_root: $repo_root,
      source_commit: $source_commit,
      prepared_at: $prepared_at,
      release_repo: $release_repo,
      dist_dir: $dist_dir,
      asset_names: $asset_names,
      checksums: $checksums,
      server_artifact: {
        os: $server_os,
        arch: $server_arch,
        archive: $server_archive
      },
      status: "prepared"
    }' > "$SUMMARY_FILE"
}

publish_release() {
  local publish_started_at
  local publish_url
  local notes
  local upload_assets=()
  local asset_path
  local source_commit
  local asset_names_json

  [[ -f "$SUMMARY_FILE" ]] || fail "Prepared release summary not found: ${SUMMARY_FILE}"

  if gh release view "$TAG" --repo "$MIDDAY_RELEASE_REPO" >/dev/null 2>&1; then
    fail "GitHub release already exists for tag ${TAG} in ${MIDDAY_RELEASE_REPO}"
  fi

  while IFS= read -r asset_path; do
    upload_assets+=("$asset_path")
  done < <(find "$RELEASE_ASSETS_DIR" -maxdepth 1 -type f \( -name '*.tar.gz' -o -name 'checksums.txt' \) | sort)

  [[ "${#upload_assets[@]}" -gt 0 ]] || fail "No prepared assets found under ${RELEASE_ASSETS_DIR}"

  publish_started_at="$(midday_now_utc_iso)"
  notes="MiddayCommander release ${TAG}"
  gh release create "$TAG" "${upload_assets[@]}" \
    --repo "$MIDDAY_RELEASE_REPO" \
    --title "$TAG" \
    --notes "$notes"

  publish_url="$(gh release view "$TAG" --repo "$MIDDAY_RELEASE_REPO" --json url --jq '.url')"
  source_commit="$(read_summary_field '.source_commit')"
  asset_names_json="$(printf '%s\n' "${upload_assets[@]##*/}" | jq -R . | jq -s .)"
  jq -n \
    --arg tag "$TAG" \
    --arg source_commit "$source_commit" \
    --arg published_at "$publish_started_at" \
    --arg github_repo "$MIDDAY_RELEASE_REPO" \
    --arg release_url "$publish_url" \
    --argjson uploaded_assets "$asset_names_json" \
    '{
      tag: $tag,
      source_commit: $source_commit,
      published_at: $published_at,
      github_repo: $github_repo,
      release_url: $release_url,
      uploaded_assets: $uploaded_assets,
      status: "published"
    }' > "$PUBLISH_FILE"
}

promote_release() {
  local archive_name
  local archive_path
  local checksums_path
  local metadata_tmp
  local published_at=""
  local source_commit
  local extracted_version
  local current_version
  local releases_root_q
  local release_dir_q
  local current_path_q
  local current_rel_q
  local archive_q
  local checksums_q
  local binary_q
  local remote_output
  local promote_time

  [[ -f "$SUMMARY_FILE" ]] || fail "Prepared release summary not found: ${SUMMARY_FILE}"

  archive_name="$(read_summary_field '.server_artifact.archive')"
  archive_path="${RELEASE_ASSETS_DIR}/${archive_name}"
  checksums_path="${RELEASE_ASSETS_DIR}/checksums.txt"
  source_commit="$(read_summary_field '.source_commit')"

  [[ -f "$archive_path" ]] || fail "Prepared server artifact is missing: ${archive_path}"
  [[ -f "$checksums_path" ]] || fail "Prepared checksums file is missing: ${checksums_path}"

  if [[ -f "$PUBLISH_FILE" ]]; then
    published_at="$(jq -r '.published_at // ""' "$PUBLISH_FILE")"
  fi

  release_dir_q="$(printf '%q' "$SERVER_RELEASE_DIR")"
  releases_root_q="$(printf '%q' "$MIDDAY_RELEASES_ROOT")"
  current_path_q="$(printf '%q' "$SERVER_CURRENT_PATH")"
  current_rel_q="$(printf '%q' "$SERVER_RELEASE_REL")"
  archive_q="$(printf '%q' "$archive_name")"
  checksums_q="$(printf '%q' "checksums.txt")"
  binary_q="$(printf '%q' "$MIDDAY_RELEASE_BINARY_NAME")"

  if midday_ssh_bash "$MIDDAY_SERVER_SSH" "[[ -e $release_dir_q ]]"; then
    fail "Server release directory already exists: ${SERVER_RELEASE_DIR}"
  fi

  midday_ssh_bash "$MIDDAY_SERVER_SSH" "mkdir -p $release_dir_q"
  scp "$archive_path" "$checksums_path" "${MIDDAY_SERVER_SSH}:${SERVER_RELEASE_DIR}/" >/dev/null

  remote_output="$(
    midday_ssh_bash "$MIDDAY_SERVER_SSH" \
      "cd $release_dir_q && tar -xzf $archive_q && rm -f $archive_q && chmod +x $binary_q && [[ -x $binary_q ]] && ./$binary_q --version"
  )"
  extracted_version="$(printf '%s\n' "$remote_output" | sed -n '1p')"

  metadata_tmp="$(mktemp "${TMPDIR:-/tmp}/midday-promote-metadata.XXXXXX")"
  promote_time="$(midday_now_utc_iso)"
  jq -n \
    --arg tag "$TAG" \
    --arg source_commit "$source_commit" \
    --arg built_at "$(read_summary_field '.prepared_at')" \
    --arg published_at "$published_at" \
    --arg github_repo "$MIDDAY_RELEASE_REPO" \
    --arg github_release_tag "$TAG" \
    --arg promoted_host "$MIDDAY_SERVER_SSH" \
    --arg promoted_at "$promote_time" \
    --arg binary_name "$MIDDAY_RELEASE_BINARY_NAME" \
    --arg binary_version "$extracted_version" \
    '{
      tag: $tag,
      source_commit: $source_commit,
      built_at: $built_at,
      published_at: $published_at,
      github_repo: $github_repo,
      github_release_tag: $github_release_tag,
      promoted_host: $promoted_host,
      promoted_at: $promoted_at,
      binary_name: $binary_name,
      binary_version: $binary_version
    }' > "$metadata_tmp"
  scp "$metadata_tmp" "${MIDDAY_SERVER_SSH}:${SERVER_RELEASE_DIR}/metadata.json" >/dev/null
  rm -f "$metadata_tmp"

  current_version="$(
    midday_ssh_bash "$MIDDAY_SERVER_SSH" \
      "tmp_link=${current_path_q}.tmp.\$\$ && ln -s $current_rel_q \"\$tmp_link\" && mv -Tf \"\$tmp_link\" $current_path_q && [[ \$(readlink $current_path_q) == $current_rel_q ]] && [[ -x $current_path_q/$binary_q ]] && $current_path_q/$binary_q --version"
  )"
  current_version="$(printf '%s\n' "$current_version" | sed -n '1p')"

  jq -n \
    --arg tag "$TAG" \
    --arg promoted_at "$promote_time" \
    --arg promoted_host "$MIDDAY_SERVER_SSH" \
    --arg release_root "$MIDDAY_RELEASES_ROOT" \
    --arg release_dir "$SERVER_RELEASE_DIR" \
    --arg current_target "$SERVER_RELEASE_REL" \
    --arg binary_version "$current_version" \
    '{
      tag: $tag,
      promoted_at: $promoted_at,
      promoted_host: $promoted_host,
      release_root: $release_root,
      release_dir: $release_dir,
      current_target: $current_target,
      binary_version: $binary_version,
      status: "promoted"
    }' > "$PROMOTE_FILE"
}

parse_build_dir() {
  local build_dir="$1"
  local base
  local parts=()
  local idx
  base="$(basename "$build_dir")"
  IFS='_' read -r -a parts <<< "$base"
  for ((idx = 0; idx < ${#parts[@]}; idx++)); do
    case "${parts[$idx]}" in
      linux|darwin|windows)
        if (( idx + 1 < ${#parts[@]} )); then
          printf '%s %s\n' "${parts[$idx]}" "${parts[$((idx + 1))]}"
          return 0
        fi
        ;;
    esac
  done
  return 1
}

if (( DRY_RUN )); then
  cat <<EOF
## MiddayCommander Release (dry run)
- Tag: ${TAG}
- Mode: ${MODE}
- MiddayCommander repo: ${MIDDAY_MAC_ROOT}
- GitHub release repo: ${MIDDAY_RELEASE_REPO}
- Server release root: ${MIDDAY_RELEASES_ROOT}
- Dist dir: ${MIDDAY_RELEASE_DIST_DIR}
- Local release storage: ${RELEASE_DIR}
- Selected server artifact: ${SERVER_TARGET_ARCHIVE}

Would run:
- validate clean annotated tag ${TAG} at HEAD
- go test ./...
- go build ./...
- goreleaser build --clean
- package archives under ${RELEASE_ASSETS_DIR}
- create ${SUMMARY_FILE}
- publish GitHub release in ${MIDDAY_RELEASE_REPO}
- promote ${SERVER_TARGET_ARCHIVE} to ${SERVER_RELEASE_DIR}
EOF
  exit 0
fi

midday_require_cmd git go ssh scp tar jq shasum gh goreleaser
midday_require_dir "$MIDDAY_MAC_ROOT" "MiddayCommander repo root"
midday_require_clean_git_worktree "$MIDDAY_MAC_ROOT"
SOURCE_COMMIT="$(midday_require_annotated_tag_at_head "$MIDDAY_MAC_ROOT" "$TAG")"

case "$MODE" in
  full)
    prepare_release "$SOURCE_COMMIT"
    publish_release
    promote_release
    ;;
  prepare-only)
    prepare_release "$SOURCE_COMMIT"
    ;;
  publish-only)
    publish_release
    ;;
  promote-only)
    promote_release
    ;;
  *)
    fail "Unsupported release mode: ${MODE}"
    ;;
esac

echo "## MiddayCommander Release"
echo "- Tag: ${TAG}"
echo "- Mode: ${MODE}"
echo "- Source commit: ${SOURCE_COMMIT}"
echo "- Summary: ${SUMMARY_FILE}"
if [[ -f "$PUBLISH_FILE" ]]; then
  echo "- Publish summary: ${PUBLISH_FILE}"
fi
if [[ -f "$PROMOTE_FILE" ]]; then
  echo "- Promote summary: ${PROMOTE_FILE}"
fi
