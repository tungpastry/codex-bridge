# Codex Bridge

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.116%2B-009688?logo=fastapi&logoColor=white)
![Gemini Auto Runner](https://img.shields.io/badge/Gemini-Headless%20Auto%20Runner-1A73E8)
![License](https://img.shields.io/badge/License-MIT-green.svg)

`codex-bridge` is a practical local router for DevOps and coding workflows across a three-node setup. It preprocesses raw tasks, logs, diffs, and reports, then routes the work to the right execution path:

- `codex` for implementation-heavy coding work
- `gemini` for safe operator workflows on the Mac mini
- `human` for risky or destructive work
- `local` for simple formatting and summarization

The project is intentionally simple. It does not automate Codex App UI control, browser automation, or AppleScript. It keeps the coding loop manual and the ops loop safe.

## Table of Contents

- [Why Codex Bridge Exists](#why-codex-bridge-exists)
- [System Overview](#system-overview)
- [How Routing Works](#how-routing-works)
- [Timing Transparency](#timing-transparency)
- [Repository Layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Summary](#api-summary)
- [Mac Automation Scripts](#mac-automation-scripts)
- [Documentation Map](#documentation-map)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Why Codex Bridge Exists

This repo exists to make mixed coding and operations work less noisy and less ambiguous:

- raw context is normalized before it reaches a model or operator
- risky tasks are blocked before they become destructive commands
- coding work becomes a clean Codex brief instead of a messy wall of context
- ops work can be auto-routed into Gemini CLI headless with a safe command whitelist
- Gemini latency is measured and saved so the Mac runner is observable instead of mysterious

The initial target repository is `MiddayCommander`, but the router is generic enough for other repos with the same workflow shape.

MiddayCommander now uses `codex-bridge` as the forward-looking home for new DevOps automation, health checks, and operator SOPs. The application code stays in the `MiddayCommander` repo, while new deploy and health workflows live here.

## System Overview

`codex-bridge` is built for this three-node topology:

| Node | Role | Main Responsibilities |
| --- | --- | --- |
| Mac mini `192.168.1.7` | Operator workstation | Codex App, Gemini CLI, Git, SSH, VS Code, safe execution runner |
| UbuntuDesktop `192.168.1.15` | Local LLM worker | FastAPI router, prompt loading, heuristics, optional Ollama refinement |
| UbuntuServer `192.168.1.30` | Runtime node | PostgreSQL, FastAPI or Flask services, cron jobs, systemd services, application logs |

Important constraints:

- Codex App stays manual. `codex-bridge` only builds a brief for the user to paste into Codex App.
- Gemini CLI is automated only for tasks routed to `gemini`, and only through safe, validated command IDs.
- Security-sensitive, destructive, or production-topology work must escalate to `human`.

## How Routing Works

`codex-bridge` follows a practical routing model:

| Route | Typical Input | Output |
| --- | --- | --- |
| `codex` | bugfix, feature, code review, setup with implementation | Markdown brief for Codex App |
| `gemini` | logs, service checks, safe triage, daily ops, low-risk review | structured Gemini job plus safe execution results |
| `human` | production schema change, auth change, firewall change, destructive data action | blocked response with escalation reason |
| `local` | compression, formatting, simple report generation | immediate local JSON or Markdown |

Route selection is based on:

- deterministic multilingual heuristics for task classification
- log and diff risk detection
- a safe command catalog for Gemini automation
- fail-closed escalation to `human` for risky patterns

## Timing Transparency

Gemini auto-run results include first-class timing metadata so operators can tell where latency lives:

- `run_id`
- `job_id`
- `timing_summary`
- `timing.pipeline_started_at`
- `timing.gemini_started_at`
- `timing.gemini_finished_at`
- `timing.exec_started_at`
- `timing.exec_finished_at`
- `timing.finished_at`
- `timing.gemini_cli_duration_ms`
- `timing.exec_duration_ms`
- `timing.total_duration_ms`

The Mac runner also appends a `## Timing` section to `final_markdown` and persists timing artifacts under `storage/gemini_runs/`.

## Repository Layout

```text
codex-bridge/
├── .env.example
├── README.md
├── app/
├── docs/
├── prompts/
├── scripts/
├── storage/
├── systemd/
├── tests/
└── requirements.txt
```

High-signal directories:

- `app/` contains FastAPI routes, schemas, services, and config
- `prompts/` stores text prompts used by the router
- `scripts/mac/` contains operator and Gemini automation scripts
- `storage/` stores snapshots, generated reports, and Gemini run artifacts
- `docs/` contains architecture, API, deployment, workflow, SOP, troubleshooting, and tutorials

## Prerequisites

Minimum baseline:

- Python `3.11+`
- `bash`, `curl`, `jq`, `ssh`
- `git`
- FastAPI-compatible runtime on `UbuntuDesktop`
- Gemini CLI installed on the Mac mini
- optional Ollama on `UbuntuDesktop` if you want future prompt refinement

Recommended host assumptions:

- Mac mini can reach `UbuntuDesktop:8787`
- Mac mini can SSH to `UbuntuServer`
- `UbuntuDesktop` can SSH to the Mac mini through alias `MacMiniGemini` for push-path runs

## Installation

### 1. Clone the repository

```bash
git clone git@github.com:tungpastry/codex-bridge.git
cd codex-bridge
```

### 2. Create the virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Create the environment file

```bash
cp .env.example .env
```

### 4. Run the development server

```bash
./scripts/run_dev.sh
```

### 5. Confirm health

```bash
curl -sS http://127.0.0.1:8787/health | jq .
```

## Configuration

Core router settings:

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

Mac automation settings:

```env
CODEX_BRIDGE_BASE_URL=http://192.168.1.15:8787
CODEX_BRIDGE_GEMINI_BIN=/opt/homebrew/bin/gemini
CODEX_BRIDGE_MAC_ROOT=/Users/macadmin/Documents/New project/codex-bridge
CODEX_BRIDGE_ALLOWED_RESTART_SERVICES=codex-bridge,postgresql,nginx
CODEX_BRIDGE_PUSH_SSH_ALIAS=MacMiniGemini
CODEX_BRIDGE_GEMINI_TIMEOUT_SECONDS=180
```

Notes:

- `CORS_ALLOW_ORIGINS_RAW` and `ALLOWED_RESTART_SERVICES_RAW` are comma-separated values, not JSON arrays.
- `scripts/push_gemini_to_mac.sh` auto-loads `CODEX_BRIDGE_PUSH_SSH_ALIAS` and `CODEX_BRIDGE_MAC_ROOT` from the repo `.env`.
- `scripts/mac/codex-bridge-run-gemini.sh` auto-loads `CODEX_BRIDGE_GEMINI_TIMEOUT_SECONDS` and tries to emit partial timing artifacts if interrupted or timed out.

## Usage

### Start the local router

```bash
./scripts/run_dev.sh
```

### Deploy on UbuntuDesktop with systemd

```bash
cd /home/nexus/codex-bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
sudo cp systemd/codex-bridge.service /etc/systemd/system/codex-bridge.service
sudo systemctl daemon-reload
sudo systemctl enable --now codex-bridge.service
sudo systemctl status codex-bridge.service --no-pager --full
```

### MiddayCommander Deploy + Health from the Mac mini

Create a local target override if you need custom values:

```bash
cp targets/middaycommander.env.example targets/middaycommander.env
```

Then run the MiddayCommander-specific wrappers:

```bash
./scripts/mac/middaycommander-deploy-router.sh
./scripts/mac/middaycommander-health.sh
./scripts/mac/middaycommander-morning-check.sh
```

These wrappers treat `codex-bridge` as the DevOps source of truth for MiddayCommander:

- the deploy wrapper syncs the local `codex-bridge` source tree to `/home/nexus/codex-bridge` on `192.168.1.15`
- the health wrapper verifies router reachability, `codex-bridge.service`, and the MiddayCommander repo state on `192.168.1.30`
- the morning check writes a timestamped Markdown report under `storage/reports/`

### Classify a coding task

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

### Build a Codex brief

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

### Dispatch a safe ops task

```bash
curl -sS http://127.0.0.1:8787/v1/dispatch/task \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Check codex-bridge service health",
    "input_kind": "task",
    "context": "Inspect service status, recent logs, and restart only if safe.",
    "repo": "codex-bridge",
    "source": "manual",
    "constraints": ["Safe commands only"]
  }' | jq .
```

### Run a full Mac-side automation flow

```bash
./scripts/mac/codex-bridge-auto.sh task "Check codex-bridge service" codex-bridge ./context.txt
```

## API Summary

Supported endpoints:

- `GET /health`
- `POST /v1/classify/task`
- `POST /v1/summarize/log`
- `POST /v1/summarize/diff`
- `POST /v1/compress/context`
- `POST /v1/brief/codex`
- `POST /v1/report/daily`
- `POST /v1/dispatch/task`

See [docs/api-reference.md](docs/api-reference.md) for full request and response details.

## Mac Automation Scripts

| Script | Purpose |
| --- | --- |
| `scripts/mac/codex-bridge-health.sh` | check router health |
| `scripts/mac/middaycommander-deploy-router.sh` | sync and restart the MiddayCommander router stack on UbuntuDesktop |
| `scripts/mac/middaycommander-health.sh` | verify the MiddayCommander 3-node topology from the Mac mini |
| `scripts/mac/middaycommander-morning-check.sh` | write a timestamped MiddayCommander morning health report |
| `scripts/mac/codex-bridge-triage-log.sh` | fetch remote journalctl logs and summarize them |
| `scripts/mac/codex-bridge-summarize-diff.sh` | summarize `git diff main...HEAD` |
| `scripts/mac/codex-bridge-make-brief.sh` | generate Markdown brief for Codex App |
| `scripts/mac/codex-bridge-morning-check.sh` | morning operational summary |
| `scripts/mac/codex-bridge-daily-report.sh` | build Markdown daily report |
| `scripts/mac/codex-bridge-dispatch.sh` | call `/v1/dispatch/task` |
| `scripts/mac/codex-bridge-run-gemini.sh` | run Gemini CLI headless and collect timing |
| `scripts/mac/codex-bridge-exec-safe.sh` | validate and execute safe commands |
| `scripts/mac/codex-bridge-auto.sh` | top-level entrypoint for route-aware automation |

## Documentation Map

- [docs/architecture.md](docs/architecture.md)
- [docs/api-reference.md](docs/api-reference.md)
- [docs/deployment.md](docs/deployment.md)
- [docs/huong-dan-su-dung.md](docs/huong-dan-su-dung.md)
- [docs/workflow.md](docs/workflow.md)
- [docs/sop.md](docs/sop.md)
- [docs/troubleshooting.md](docs/troubleshooting.md)
- [docs/tutorials/coding-task.md](docs/tutorials/coding-task.md)
- [docs/tutorials/ops-incident.md](docs/tutorials/ops-incident.md)

## Roadmap

Short-term:

- keep expanding MiddayCommander-specific DevOps wrappers and SOPs from this repo
- tighten structured validation for Gemini plan JSON
- add more service-aware safe command templates
- expand MiddayCommander-focused examples

Future:

- optional richer Ollama-assisted refinement while keeping heuristics as the default fallback
- richer reporting over accumulated Gemini run artifacts
- more tutorials for incident response and code review patterns

## Contributing

Contributions are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md) for setup, testing, and pull request guidance.

## License

This project is released under the [MIT License](LICENSE).

## Contact

- GitHub: [tungpastry](https://github.com/tungpastry)
- Email: [bakerthanhtung@gmail.com](mailto:bakerthanhtung@gmail.com)
