# Workflow

## 1. Build New Feature

1. Gather issue context or failing behavior.
2. Run `scripts/mac/codex-bridge-dispatch.sh task ...`.
3. If route is `codex`, extract `codex_brief_markdown`.
4. Paste the brief into Codex App.
5. Implement and review the patch manually.

Typical target: `MiddayCommander` feature or bugfix work.

## 2. Incident Response

1. Run `scripts/mac/codex-bridge-triage-log.sh <service>`.
2. If route is `gemini`, let `scripts/mac/codex-bridge-auto.sh` invoke Gemini CLI and execute safe commands.
3. Review the final markdown summary.
4. If route escalates to `human`, stop automation and review manually.

Typical target: runtime issue on `UbuntuServer`.

## 3. Daily Ops

1. Run `scripts/mac/codex-bridge-morning-check.sh`.
2. Review router health plus key service states.
3. Collect notes into `scripts/mac/codex-bridge-daily-report.sh`.
4. Share the generated markdown report.

Typical target: daily operational summary and triage queue.
