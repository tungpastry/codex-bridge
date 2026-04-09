# Troubleshooting

This document captures the most important issues seen while bringing up and upgrading `codex-bridge`.

Related docs:

- [Deployment](./deployment.md)
- [Architecture](./architecture.md)
- [API Reference](./api-reference.md)
- [Vietnamese version](./troubleshooting-vi.md)

## The Router Will Not Start

### Symptom

- `systemd` shows the service starting and then dying
- local `curl http://127.0.0.1:8787/health` returns connection refused

### Likely causes

- invalid `.env` values
- unreadable profile files
- missing dependencies
- bad runtime paths

### Fix

- check `journalctl -u codex-bridge.service -n 120 --no-pager`
- confirm `PROMPTS_DIR`, `STORAGE_DIR`, `RUN_INDEX_DB_PATH`, and `PROFILES_DIR`
- verify startup migration logs are present

## Hidden AppleDouble Profile Files Break the Loader

### Symptom

- the service fails after syncing files from macOS
- profile loading throws a decode error

### Likely cause

- `._*.yaml` files or `.DS_Store` files were copied into the profiles directory

### Fix

- remove hidden macOS sidecar files from `app/profiles/`
- keep deployment sync rules from copying `._*` and `.DS_Store`
- use the updated profile loader that ignores hidden files

## Health Works Locally but Not Over LAN

### Symptom

- `curl http://127.0.0.1:8787/health` works on the router
- `curl http://192.168.1.15:8787/health` fails from the Mac

### Likely cause

- firewall or LAN reachability issue

### Fix

- confirm the app is listening on `0.0.0.0:8787`
- check UFW or other firewall rules
- confirm the router IP did not change

## `ssh MacMiniGemini` Fails with `Connection refused`

### Symptom

- router push path to the Mac fails immediately

### Likely cause

- Remote Login is disabled on the Mac
- SSH alias or key setup is incomplete

### Fix

- enable Remote Login on the Mac
- confirm `~/.ssh/config` contains `MacMiniGemini`
- test `ssh MacMiniGemini 'hostname && whoami'`

## Gemini Runner Fails with `node: No such file or directory`

### Symptom

- Gemini CLI works in an interactive terminal
- the same command fails through SSH or a script

### Likely cause

- non-interactive shells do not load the Homebrew `PATH`

### Fix

- bootstrap Homebrew shell environment inside the runner
- confirm the script can find both `gemini` and `node`

## Gemini CLI Requests Browser Authentication

### Symptom

- the runner blocks quickly with an authentication-related status
- Gemini CLI outputs a browser-auth prompt

### Likely cause

- headless auth is not configured

### Fix

- provide cached credentials or environment-based authentication
- confirm the runner can export the required auth variables from `.env`

## Gemini Returns Empty or Non-JSON Output

### Symptom

- the run blocks before safe execution starts
- `final_markdown` says Gemini did not return valid JSON

### Likely cause

- Gemini output includes banner text or non-JSON lines
- model output is malformed

### Fix

- review `<run_id>-gemini-output.json`
- confirm the runner is using the JSON extraction path that tolerates banner text
- verify the prompt still instructs Gemini to return JSON only

## Internal Callback Does Not Update the Run Index

### Symptom

- the Mac runner prints a final result
- `/v1/runs/{run_id}` still shows `awaiting_execution`

### Likely cause

- `CODEX_BRIDGE_BASE_URL` is missing or wrong on the Mac
- `CODEX_BRIDGE_INTERNAL_API_TOKEN` does not match the router

### Fix

- confirm `CODEX_BRIDGE_BASE_URL=http://192.168.1.15:8787`
- confirm the token is identical on both hosts
- retry the run and inspect router logs

## The Wrong Host Is Used for `systemctl` or `journalctl`

### Symptom

- the run reaches execution
- service commands are sent to the wrong node

### Likely cause

- the relevant profile is missing `preferred_command_hosts`
- the router is running an older prompt/profile version

### Fix

- confirm the profile contains the expected host preferences
- redeploy the router if the prompt or profile changed
- inspect `gemini_job.preferred_command_hosts` in the dispatch response

## The Service Is Running but the Update Did Not Take Effect

### Symptom

- `systemctl status` looks healthy
- behavior still matches an older code version

### Likely cause

- the source tree was synced but the service was not restarted
- the router host is using a synced tree rather than a git checkout

### Fix

- confirm the updated files actually exist on the router
- restart `codex-bridge.service`
- verify the new behavior through `/health?depth=full` or a route-specific smoke test
