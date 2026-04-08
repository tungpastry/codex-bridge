# Architecture

## Three-Node Layout

- Mac mini `192.168.1.7`
  - Codex App for coding
  - Gemini CLI for ops automation
  - Git, SSH, VS Code
- UbuntuDesktop `192.168.1.15`
  - runs `codex-bridge` FastAPI router
  - preprocesses logs, diffs, tasks, and reports
  - optionally talks to local Ollama for prompt refinement
- UbuntuServer `192.168.1.30`
  - runtime services
  - PostgreSQL
  - FastAPI or Flask apps
  - cron jobs
  - systemd services
  - application logs

## Why Preprocess Before Codex Or Gemini

`codex-bridge` exists to keep routing deterministic and practical:

- it normalizes raw context
- it classifies risk
- it chooses `codex`, `gemini`, `human`, or `local`
- it builds a clean brief for Codex App
- it prepares a safe structured execution job for Gemini CLI

This avoids sending every raw task directly into a large model loop and keeps operator intent explicit.

## Important Constraint

Codex App does not automatically use the GPU node on `192.168.1.15`.

If the system needs local-model preprocessing, that happens because `codex-bridge` is explicitly built as a custom router. The coding workflow is still:

1. gather context
2. generate Codex brief
3. paste brief into Codex App
4. implement and review manually in Codex App or editor

## Gemini Automation Design

For `gemini` tasks:

1. router produces a structured `gemini_job`
2. Mac mini runs Gemini CLI headless
3. Gemini returns structured JSON with command IDs, not arbitrary shell
4. `codex-bridge-exec-safe.sh` validates commands against a whitelist
5. safe commands are executed locally or over SSH
6. risky or invalid plans fail closed to `human`

## Why V1 Avoids YOLO Tool Autonomy

V1 does not rely on Gemini tool autonomy or YOLO mode because:

- approval prompts can hang unattended workflows
- arbitrary shell text is harder to validate deterministically
- a command ID whitelist is simpler to audit
- fail-closed behavior is easier to reason about in production
