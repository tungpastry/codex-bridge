# Codex Bridge

`codex-bridge` is a practical local router for DevOps + coding workflows across three nodes:

- Mac mini `192.168.1.7`: operator workstation, Codex App, Gemini CLI runner
- UbuntuDesktop `192.168.1.15`: local LLM worker running the FastAPI router
- UbuntuServer `192.168.1.30`: runtime node with services, PostgreSQL, cron, and logs

The product goal is simple:

1. accept raw task, log, diff, or report input
2. preprocess and classify it on the local router
3. route it to `codex`, `gemini`, `human`, or `local`
4. auto-run Gemini CLI on the Mac mini for safe ops tasks
5. generate a clean brief for manual paste into Codex App for coding tasks

## Architecture

- `Codex App` stays manual. `codex-bridge` never automates UI control, browser automation, or AppleScript.
- `Gemini CLI` is automated only for tasks routed to `gemini`, and only through a safe command whitelist.
- `human` is always the fallback for risky or destructive work such as production schema changes, auth changes, firewall changes, or destructive data operations.
- Gemini auto-run results now include `run_id`, `timing_summary`, and a structured `timing` object so operators can see both Gemini headless latency and total pipeline time.

## Repository Layout

```text
codex-bridge/
├── .env.example
├── README.md
├── requirements.txt
├── app/
├── prompts/
├── storage/
├── systemd/
├── scripts/
├── docs/
└── tests/
```

## Endpoint Summary

- `GET /health`
- `POST /v1/classify/task`
- `POST /v1/summarize/log`
- `POST /v1/summarize/diff`
- `POST /v1/compress/context`
- `POST /v1/brief/codex`
- `POST /v1/report/daily`
- `POST /v1/dispatch/task`

## Route Selection

- `codex`: bugfix, feature, setup, implementation-heavy review
- `gemini`: logs, service checks, deploy triage, lightweight review, operator checklist
- `human`: risky, destructive, security-sensitive, auth-sensitive, firewall-sensitive, or production database-sensitive work
- `local`: simple compression or report formatting that does not need external execution

## Local Dev Setup

```bash
cd codex-bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
./scripts/run_dev.sh
```

Health check:

```bash
curl -sS http://127.0.0.1:8787/health | jq .
```

## `.env` Setup

Required defaults:

```env
APP_NAME=codex-bridge
APP_ENV=dev
APP_HOST=0.0.0.0
APP_PORT=8787
LLM_BACKEND=ollama
LLM_BASE_URL=http://127.0.0.1:11434
LLM_MODEL=gemma3:1b-it-qat
LLM_TIMEOUT_SECONDS=120
PROMPTS_DIR=/home/nexus/codex-bridge/prompts
STORAGE_DIR=/home/nexus/codex-bridge/storage
CORS_ALLOW_ORIGINS_RAW=http://localhost,http://127.0.0.1
ALLOWED_RESTART_SERVICES_RAW=codex-bridge,postgresql,nginx
```

Mac automation variables:

```env
CODEX_BRIDGE_BASE_URL=http://192.168.1.15:8787
CODEX_BRIDGE_GEMINI_BIN=/opt/homebrew/bin/gemini
CODEX_BRIDGE_MAC_ROOT=/Users/macadmin/Documents/New project/codex-bridge
CODEX_BRIDGE_ALLOWED_RESTART_SERVICES=codex-bridge,postgresql,nginx
CODEX_BRIDGE_PUSH_SSH_ALIAS=MacMiniGemini
CODEX_BRIDGE_GEMINI_TIMEOUT_SECONDS=180
```

`scripts/push_gemini_to_mac.sh` auto-loads the repo `.env`, so `CODEX_BRIDGE_MAC_ROOT` and `CODEX_BRIDGE_PUSH_SSH_ALIAS` do not need to be passed on every run.
`scripts/mac/codex-bridge-run-gemini.sh` also auto-loads `CODEX_BRIDGE_GEMINI_TIMEOUT_SECONDS`, and now tries to emit partial `timing.json` plus `final.json` when interrupted or when Gemini headless exceeds the timeout.

## Run Dev

```bash
./scripts/run_dev.sh
```

## Systemd Install

```bash
cd /home/nexus/codex-bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
sudo cp systemd/codex-bridge.service /etc/systemd/system/codex-bridge.service
sudo systemctl daemon-reload
sudo systemctl enable --now codex-bridge.service
sudo systemctl status codex-bridge.service --no-pager
```

## Mac Scripts

- `scripts/mac/codex-bridge-health.sh`
- `scripts/mac/codex-bridge-triage-log.sh`
- `scripts/mac/codex-bridge-summarize-diff.sh`
- `scripts/mac/codex-bridge-make-brief.sh`
- `scripts/mac/codex-bridge-morning-check.sh`
- `scripts/mac/codex-bridge-daily-report.sh`
- `scripts/mac/codex-bridge-dispatch.sh`
- `scripts/mac/codex-bridge-run-gemini.sh`
- `scripts/mac/codex-bridge-exec-safe.sh`
- `scripts/mac/codex-bridge-auto.sh`

## Curl Examples

Classify a coding issue:

```bash
curl -sS http://127.0.0.1:8787/v1/classify/task \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "MiddayCommander transfer panic",
    "context": "Go test is failing with panic in transfer queue after remote retry.",
    "repo": "MiddayCommander",
    "source": "manual",
    "constraints": ["Keep patch minimal", "Do not redesign transfer engine"]
  }' | jq .
```

Build a Codex brief:

```bash
curl -sS http://127.0.0.1:8787/v1/brief/codex \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Fix MiddayCommander transfer retry panic",
    "repo": "MiddayCommander",
    "context": "Panic occurs after retry exhaustion in remote transfer queue.",
    "constraints": ["Small patch", "Preserve current UX"]
  }' | jq -r '.brief_markdown'
```

Dispatch an ops task:

```bash
curl -sS http://127.0.0.1:8787/v1/dispatch/task \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Check codex-bridge service health",
    "input_kind": "task",
    "context": "Need to inspect service status, logs, and restart only if safe.",
    "repo": "codex-bridge",
    "source": "manual",
    "constraints": ["Safe commands only"]
  }' | jq .
```
