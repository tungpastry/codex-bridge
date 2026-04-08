# Workflow

This document describes the three core workflows that `codex-bridge` is designed to support in v1.

## 1. Build New Feature or Bugfix

Typical target:

- `MiddayCommander` implementation work
- failing build or test triage
- focused code review that likely leads to a patch

Recommended flow:

1. Gather the task title, repo name, and relevant context.
2. Call `scripts/mac/codex-bridge-dispatch.sh task ...` or `scripts/mac/codex-bridge-make-brief.sh ...`.
3. If the route is `codex`, capture `codex_brief_markdown`.
4. Paste that brief into Codex App.
5. Implement the patch manually in Codex App or your editor.
6. Run local tests or smoke checks.

MiddayCommander-specific note:

- coding work still stays in the `MiddayCommander` repo
- new deploy and health automation for that repo now lives in `codex-bridge`

Why this route exists:

- coding work benefits from cleaner context and tighter acceptance criteria
- the router removes noisy logs and raw issue chatter before Codex sees the problem
- manual review remains part of the flow

Stop conditions:

- if the task includes production auth, schema, firewall, or destructive data signals, escalate to `human`
- if the task is actually an ops incident rather than a code change, reroute to `gemini`

## 2. Incident Response

Typical target:

- runtime issue on `UbuntuServer`
- failing `systemd` service
- recent `journalctl` error triage
- low-risk inspection and restart workflows

Recommended flow:

1. Run `scripts/mac/codex-bridge-triage-log.sh <service>`.
2. Review the JSON summary from `/v1/summarize/log`.
3. If the route is `gemini`, run `scripts/mac/codex-bridge-auto.sh` or push a prepared Gemini job to the Mac.
4. Let Gemini produce a structured plan with safe command IDs.
5. Let `codex-bridge-exec-safe.sh` validate and run the approved commands.
6. Review `final_markdown`, `timing_summary`, and the saved run artifacts.

What this workflow is good at:

- recent service health inspection
- checking whether a service is active or failed
- reading recent logs
- inspecting port state, memory, disk, and uptime
- restarting an allowlisted service if the plan remains safe

Stop conditions:

- if the response route becomes `human`
- if the plan includes a forbidden command or host
- if the issue involves production schema changes, auth changes, firewall changes, or destructive operations

## 3. Daily Ops

Typical target:

- morning health checks
- operator summaries
- ongoing triage notes
- end-of-day reporting

Recommended flow:

1. Run `scripts/mac/codex-bridge-health.sh`.
2. Run `scripts/mac/codex-bridge-morning-check.sh`.
3. Collect any completed items, open issues, or next actions.
4. Run `scripts/mac/codex-bridge-daily-report.sh`.
5. Share the generated Markdown report with the team or keep it as a local operations record.

MiddayCommander Deploy + Health path:

1. Run `scripts/mac/middaycommander-deploy-router.sh` when the router deployment needs refreshing on `192.168.1.15`.
2. Run `scripts/mac/middaycommander-health.sh` to verify the 3-node topology.
3. Run `scripts/mac/middaycommander-morning-check.sh` to save a timestamped Markdown health report.
4. Use the report as the operator handoff artifact instead of re-checking the same state manually.

Expected outputs:

- short router health summary
- service state summary
- Markdown report with `Done`, `Open Issues`, and `Next Actions`

## Cross-Workflow Notes

Things that stay true in every workflow:

- `codex-bridge` preprocesses first
- route choice is explicit
- MiddayCommander DevOps ownership now starts here, not in the product repo
- Codex App is never auto-controlled
- Gemini CLI is only used within the safe-command boundary
- risky work is blocked instead of being pushed through “just in case”
