# Troubleshooting

This document captures the most common problems seen while bringing up `codex-bridge` across the Mac mini and Ubuntu nodes.

## The Router Will Not Start

### Symptom

`uvicorn` exits during startup and mentions `pydantic_settings` or `.env` parsing.

### Likely cause

A CSV setting such as `CORS_ALLOW_ORIGINS_RAW` or `ALLOWED_RESTART_SERVICES_RAW` was written in an invalid format.

### Fix

Use comma-separated values, not a JSON array:

```env
CORS_ALLOW_ORIGINS_RAW=http://localhost,http://127.0.0.1
ALLOWED_RESTART_SERVICES_RAW=codex-bridge,postgresql,nginx
```

## The Mac Uses the Wrong Prompt or Storage Path

### Symptom

The app on the Mac seems to point at `/home/nexus/codex-bridge/...` instead of local repo paths.

### Likely cause

The `.env` was copied from the Ubuntu deployment environment.

### Fix

Update `.env` on the Mac or rely on the local fallback logic:

```env
PROMPTS_DIR=/Users/macadmin/Documents/New project/codex-bridge/prompts
STORAGE_DIR=/Users/macadmin/Documents/New project/codex-bridge/storage
```

## Health Works Locally but Not Over LAN

### Symptom

`curl http://127.0.0.1:8787/health` works on UbuntuDesktop, but `curl http://192.168.1.15:8787/health` fails from the Mac.

### Likely cause

- local firewall
- wrong bind address
- stale LAN IP

### Fix

Check:

```bash
sudo systemctl status codex-bridge.service --no-pager --full
ss -ltnp | grep 8787
sudo ufw status verbose
```

The service should bind to `0.0.0.0:8787`.

## `ssh MacMiniGemini` Fails With Connection Refused

### Symptom

UbuntuDesktop cannot push jobs to the Mac.

### Likely cause

Remote Login is disabled on the Mac or SSH key trust is missing.

### Fix

On the Mac:

```bash
sudo systemsetup -setremotelogin on
```

Then make sure the UbuntuDesktop public key is in `~/.ssh/authorized_keys` on the Mac and retest:

```bash
ssh MacMiniGemini 'hostname && whoami'
```

## Gemini Runner Fails With `node: No such file or directory`

### Symptom

`codex-bridge-run-gemini.sh` starts over SSH but Gemini CLI does not launch.

### Likely cause

Non-interactive SSH sessions on macOS often do not load the Homebrew PATH.

### Fix

The runner already bootstraps Homebrew PATH. If you still see this error, confirm:

```bash
ls -l /opt/homebrew/bin/gemini
ls -l /opt/homebrew/bin/node
```

Also confirm Homebrew is installed under `/opt/homebrew`.

## Gemini Returns Invalid JSON

### Symptom

The runner writes a blocked result saying Gemini did not return valid JSON or the extracted plan payload was invalid.

### Likely cause

- Gemini CLI responded with non-JSON output
- the JSON was wrapped unexpectedly
- the run was interrupted mid-output

### Fix

Inspect these artifacts:

- `storage/gemini_runs/<run_id>-gemini-output.json`
- `storage/gemini_runs/<run_id>-plan.json`
- `storage/gemini_runs/<run_id>-final.json`

If the response is consistently malformed, tighten the prompt or run in mock mode to validate the rest of the pipeline.

## Gemini Seems to Hang or Feel Slow

### Symptom

The Mac runner appears stuck and it is unclear whether the delay is in Gemini itself or command execution.

### Fix

Inspect:

- `timing_summary`
- `storage/gemini_runs/<run_id>-timing.json`
- `storage/gemini_runs/<run_id>-final.json`

The timing object separates:

- Gemini headless duration
- safe command execution duration
- total pipeline duration

If the run times out or receives `TERM`, the runner now tries to emit partial timing artifacts instead of losing the whole trace.

## `push_gemini_to_mac.sh` Fails With Shell Syntax Error

### Symptom

You run:

```bash
./scripts/push_gemini_to_mac.sh --job-file <path-to-gemini-job.json>
```

and Bash reports `syntax error near unexpected token newline`.

### Likely cause

`<path-to-gemini-job.json>` is a placeholder, not a literal argument.

### Fix

Use a real path:

```bash
./scripts/push_gemini_to_mac.sh --job-file storage/gemini_runs/manual-push-test-job.json
```

## `dispatch/task` Returns 500

### Symptom

The router returns an internal server error when building a Gemini job.

### Likely cause

Prompt rendering failed or the prompt file contains unescaped braces in JSON examples.

### Fix

Check:

```bash
journalctl -u codex-bridge.service -n 100 --no-pager
```

Then review the relevant prompt file under `prompts/`, especially `build_gemini_job.txt`.

## The Service Is Running but the Repo Update Did Not Take Effect

### Symptom

New code exists under `/home/nexus/codex-bridge`, but the router behavior still looks old.

### Likely cause

The systemd service was not restarted after pulling code.

### Fix

```bash
cd /home/nexus/codex-bridge
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart codex-bridge.service
sudo systemctl status codex-bridge.service --no-pager --full
```
