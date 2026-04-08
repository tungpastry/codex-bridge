#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${CODEX_BRIDGE_SMOKE_PORT:-18787}"
BASE_URL="http://127.0.0.1:${PORT}"
DEFAULT_PYTHON_BIN="python3"
if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  DEFAULT_PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
fi
PYTHON_BIN="${CODEX_BRIDGE_PYTHON_BIN:-$DEFAULT_PYTHON_BIN}"
TMP_DIR="$(mktemp -d)"
SERVER_LOG="${TMP_DIR}/server.log"

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

export PYTHONPYCACHEPREFIX="${TMP_DIR}/pycache"
export PROMPTS_DIR="${ROOT_DIR}/prompts"
export STORAGE_DIR="${ROOT_DIR}/storage"

cd "$ROOT_DIR"

echo "== import sanity"
"$PYTHON_BIN" -c 'from app.main import app; print(app.title)'

echo "== unittest"
"$PYTHON_BIN" -m unittest tests.test_router

echo "== start server"
"$PYTHON_BIN" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" >"$SERVER_LOG" 2>&1 &
SERVER_PID="$!"
sleep 2

if curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
  echo "== health"
  curl -fsS "${BASE_URL}/health" | jq .

  echo "== classify"
  curl -fsS "${BASE_URL}/v1/classify/task" \
    -H "Content-Type: application/json" \
    -d '{
      "title":"MiddayCommander build failure",
      "context":"Go test failed with panic in remote transfer retry path",
      "repo":"MiddayCommander",
      "source":"smoke",
      "constraints":["Keep patch small"]
    }' | jq .

  echo "== diff summary"
  curl -fsS "${BASE_URL}/v1/summarize/diff" \
    -H "Content-Type: application/json" \
    -d '{
      "repo":"MiddayCommander",
      "diff_text":"diff --git a/internal/fs/router.go b/internal/fs/router.go\n+++ b/internal/fs/router.go\n@@\n+if err != nil { return err }\n"
    }' | jq .

  echo "== report"
  curl -fsS "${BASE_URL}/v1/report/daily" \
    -H "Content-Type: application/json" \
    -d '{
      "items":["Done: added health route","Open: need smoke check","Next: verify dispatch flow"]
    }' | jq .

  echo "== codex brief"
  curl -fsS "${BASE_URL}/v1/brief/codex" \
    -H "Content-Type: application/json" \
    -d '{
      "title":"Fix MiddayCommander retry panic",
      "repo":"MiddayCommander",
      "context":"Retry path panics after final remote failure",
      "constraints":["Minimal patch"]
    }' | jq -r '.brief_markdown'

  echo "== dispatch"
  curl -fsS "${BASE_URL}/v1/dispatch/task" \
    -H "Content-Type: application/json" \
    -d '{
      "title":"Inspect codex-bridge health",
      "input_kind":"task",
      "context":"Check service status and router health only with safe commands",
      "repo":"codex-bridge",
      "source":"smoke",
      "constraints":["Safe commands only"]
    }' | jq .
else
  echo "== uvicorn bind unavailable, falling back to in-process smoke"
  cat "$SERVER_LOG"
  "${PYTHON_BIN}" tests/smoke_runner.py
fi

echo "== gemini runner timing"
RUNNER_ROOT="${TMP_DIR}/runner-root"
RUNNER_JOB_FILE="${TMP_DIR}/runner-job.json"
RUNNER_MOCK_FILE="${TMP_DIR}/runner-mock.json"
RUNNER_OUTPUT_FILE="${TMP_DIR}/runner-output.json"

cat >"$RUNNER_JOB_FILE" <<'EOF'
{
  "job_id": "smoke-gemini-job-ok",
  "mode": "ops_auto",
  "title": "Inspect local uptime",
  "repo": "codex-bridge",
  "problem_summary": "Inspect local uptime",
  "context_digest": "Use a safe local uptime command.",
  "constraints": ["Safe commands only"],
  "allowed_hosts": ["local", "UbuntuDesktop", "UbuntuServer"],
  "allowed_command_ids": ["uptime"],
  "output_contract": {
    "summary": "Short human-readable summary",
    "confidence": "low|medium|high",
    "needs_human": "true|false",
    "why": "Why the plan is safe or why it needs escalation",
    "commands": "Array of {host, command_id, args, reason}",
    "final_markdown": "Operator-ready markdown summary"
  },
  "prompt": "Return JSON only."
}
EOF

cat >"$RUNNER_MOCK_FILE" <<'EOF'
{
  "response": "{\"summary\": \"Inspecting local uptime.\", \"confidence\": \"high\", \"needs_human\": false, \"why\": \"This uses a safe local read-only command.\", \"commands\": [{\"host\": \"local\", \"command_id\": \"uptime\", \"args\": {}, \"reason\": \"Check local uptime.\"}], \"final_markdown\": \"### Mock Plan\"}"
}
EOF

CODEX_BRIDGE_MAC_ROOT="$RUNNER_ROOT" \
CODEX_BRIDGE_GEMINI_MOCK_RESPONSE_FILE="$RUNNER_MOCK_FILE" \
  "${ROOT_DIR}/scripts/mac/codex-bridge-run-gemini.sh" --job-file "$RUNNER_JOB_FILE" >"$RUNNER_OUTPUT_FILE"

jq -e '.run_id == "smoke-gemini-job-ok"' "$RUNNER_OUTPUT_FILE" >/dev/null
jq -e '.job_id == "smoke-gemini-job-ok"' "$RUNNER_OUTPUT_FILE" >/dev/null
jq -e '.timing.gemini_cli_duration_ms >= 0' "$RUNNER_OUTPUT_FILE" >/dev/null
jq -e '.timing.total_duration_ms >= .timing.gemini_cli_duration_ms' "$RUNNER_OUTPUT_FILE" >/dev/null
jq -e '.final_markdown | contains("## Timing")' "$RUNNER_OUTPUT_FILE" >/dev/null
test -f "${RUNNER_ROOT}/storage/gemini_runs/smoke-gemini-job-ok-job.json"
test -f "${RUNNER_ROOT}/storage/gemini_runs/smoke-gemini-job-ok-gemini-output.json"
test -f "${RUNNER_ROOT}/storage/gemini_runs/smoke-gemini-job-ok-plan.json"
test -f "${RUNNER_ROOT}/storage/gemini_runs/smoke-gemini-job-ok-exec-results.json"
test -f "${RUNNER_ROOT}/storage/gemini_runs/smoke-gemini-job-ok-timing.json"
test -f "${RUNNER_ROOT}/storage/gemini_runs/smoke-gemini-job-ok-final.json"
cat "$RUNNER_OUTPUT_FILE" | jq .

echo "== blocked gemini runner timing"
RUNNER_BLOCKED_JOB_FILE="${TMP_DIR}/runner-blocked-job.json"
RUNNER_BLOCKED_MOCK_FILE="${TMP_DIR}/runner-blocked-mock.json"
RUNNER_BLOCKED_OUTPUT_FILE="${TMP_DIR}/runner-blocked-output.json"

cat >"$RUNNER_BLOCKED_JOB_FILE" <<'EOF'
{
  "job_id": "smoke-gemini-job-blocked",
  "mode": "ops_auto",
  "title": "Blocked plan",
  "repo": "codex-bridge",
  "problem_summary": "Needs human review",
  "context_digest": "Human escalation test.",
  "constraints": ["Safe commands only"],
  "allowed_hosts": ["local", "UbuntuDesktop", "UbuntuServer"],
  "allowed_command_ids": ["uptime"],
  "output_contract": {
    "summary": "Short human-readable summary",
    "confidence": "low|medium|high",
    "needs_human": "true|false",
    "why": "Why the plan is safe or why it needs escalation",
    "commands": "Array of {host, command_id, args, reason}",
    "final_markdown": "Operator-ready markdown summary"
  },
  "prompt": "Return JSON only."
}
EOF

cat >"$RUNNER_BLOCKED_MOCK_FILE" <<'EOF'
{
  "response": "{\"summary\": \"Needs human review.\", \"confidence\": \"low\", \"needs_human\": true, \"why\": \"Manual review required.\", \"commands\": [], \"final_markdown\": \"### Blocked Plan\"}"
}
EOF

if CODEX_BRIDGE_MAC_ROOT="$RUNNER_ROOT" \
  CODEX_BRIDGE_GEMINI_MOCK_RESPONSE_FILE="$RUNNER_BLOCKED_MOCK_FILE" \
  "${ROOT_DIR}/scripts/mac/codex-bridge-run-gemini.sh" --job-file "$RUNNER_BLOCKED_JOB_FILE" >"$RUNNER_BLOCKED_OUTPUT_FILE"; then
  echo "Expected blocked Gemini runner to exit non-zero." >&2
  exit 1
fi

jq -e '.status == "blocked"' "$RUNNER_BLOCKED_OUTPUT_FILE" >/dev/null
jq -e '.run_id == "smoke-gemini-job-blocked"' "$RUNNER_BLOCKED_OUTPUT_FILE" >/dev/null
jq -e '.timing.total_duration_ms >= 0' "$RUNNER_BLOCKED_OUTPUT_FILE" >/dev/null
jq -e '.final_markdown | contains("## Timing")' "$RUNNER_BLOCKED_OUTPUT_FILE" >/dev/null
test -f "${RUNNER_ROOT}/storage/gemini_runs/smoke-gemini-job-blocked-timing.json"
test -f "${RUNNER_ROOT}/storage/gemini_runs/smoke-gemini-job-blocked-final.json"
cat "$RUNNER_BLOCKED_OUTPUT_FILE" | jq .

echo "Smoke test passed."
