# SOP

## Morning SOP

1. Run `scripts/mac/codex-bridge-health.sh`.
2. Run `scripts/mac/codex-bridge-morning-check.sh`.
3. Review any failed or inactive services on `UbuntuServer`.
4. Escalate risky findings to a human before any production change.

## Build SOP

1. Gather issue or feature context.
2. Run `scripts/mac/codex-bridge-dispatch.sh task ...`.
3. If route is `codex`, paste the brief into Codex App.
4. Keep implementation scoped and verify with local tests or smoke checks.

## Incident SOP

1. Run `scripts/mac/codex-bridge-triage-log.sh <service>`.
2. If safe, run `scripts/mac/codex-bridge-auto.sh log ...`.
3. Review executed commands and final markdown in `storage/gemini_runs/`.
4. Stop immediately if route becomes `human`.

## End-of-Day SOP

1. Collect completed items, open issues, and next actions.
2. Run `scripts/mac/codex-bridge-daily-report.sh`.
3. Save or share the markdown report.
4. Confirm any pending risky items are documented for human follow-up.
