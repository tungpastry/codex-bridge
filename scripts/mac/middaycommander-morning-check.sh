#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/mac/middaycommander-common.sh
source "${SCRIPT_DIR}/middaycommander-common.sh"

usage() {
  cat <<'EOF'
Usage: middaycommander-morning-check.sh [--dry-run] [--help]

Run the MiddayCommander health check and write a timestamped Markdown report
under storage/reports/ on the Mac mini.
EOF
}

DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
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

midday_load_env
midday_require_cmd mkdir date

timestamp="$(midday_now_utc)"
report_file="${MIDDAY_REPORTS_DIR}/middaycommander-morning-${timestamp}.md"

if (( DRY_RUN )); then
  cat <<EOF
## MiddayCommander Morning Check (dry run)
- Report file: ${report_file}
- Health script: ${SCRIPT_DIR}/middaycommander-health.sh
- Router URL: ${MIDDAY_ROUTER_BASE_URL}
- UbuntuDesktop: ${MIDDAY_DESKTOP_SSH}
- UbuntuServer: ${MIDDAY_SERVER_SSH}
- Release root: ${MIDDAY_RELEASES_ROOT}

Would run:
- ${SCRIPT_DIR}/middaycommander-health.sh
- write a timestamped Markdown report under ${MIDDAY_REPORTS_DIR}
EOF
  exit 0
fi

mkdir -p "$MIDDAY_REPORTS_DIR"

set +e
health_output="$("${SCRIPT_DIR}/middaycommander-health.sh" 2>&1)"
health_status=$?
set -e

cat >"$report_file" <<EOF
# MiddayCommander Morning Check

- Generated At (UTC): ${timestamp}
- Router URL: ${MIDDAY_ROUTER_BASE_URL}
- UbuntuDesktop: ${MIDDAY_DESKTOP_SSH}
- UbuntuServer: ${MIDDAY_SERVER_SSH}

${health_output}
EOF

printf 'Report written to %s\n' "$report_file"
if [[ $health_status -ne 0 ]]; then
  exit "$health_status"
fi
