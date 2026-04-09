# SOP

This document turns the main workflows into repeatable operator checklists.

Related docs:

- [Workflow](./workflow.md)
- [Troubleshooting](./troubleshooting.md)
- [MiddayCommander target docs](./targets/middaycommander.md)
- [Vietnamese version](./sop-vi.md)

## Morning Check SOP

Goal:

- confirm the router is reachable
- confirm the key nodes are visible
- catch obvious incidents early

Checklist:

1. Run `scripts/mac/codex-bridge-health.sh`.
2. Run `scripts/mac/codex-bridge-morning-check.sh`.
3. Review the generated report under `storage/reports/`.
4. Review failed, inactive, or suspicious services.
5. Escalate risky production findings to a human before any change is made.

## Coding Intake SOP

Goal:

- keep coding tasks clean, scoped, and reviewable

Checklist:

1. Gather the issue title, repo, and raw context.
2. Run `scripts/mac/codex-bridge-dispatch.sh task ...` or `scripts/mac/codex-bridge-make-brief.sh ...`.
3. If the route is `codex`, copy the generated brief into Codex App.
4. Keep the implementation scoped to the stated goal and constraints.
5. Run local tests or smoke checks in the target repo.
6. Review the patch before commit.

## Incident SOP

Goal:

- inspect the system safely
- avoid destructive improvisation under pressure

Checklist:

1. Run `scripts/mac/codex-bridge-triage-log.sh <service>` or dispatch the problem statement.
2. Review the summary and recommended route.
3. If safe, run `scripts/mac/codex-bridge-auto.sh ...` or push a prepared Gemini job to the Mac.
4. Review the executed commands, final Markdown, and timing output.
5. Stop immediately if the route becomes `human` or the plan is blocked.

## Deployment Verification SOP

Goal:

- confirm the router is healthy after deploy or upgrade

Checklist:

1. Verify `systemctl status codex-bridge.service`.
2. Verify `GET /health`.
3. Verify `GET /health?depth=full`.
4. Check migration log entries for the run index.
5. Run a small dispatch smoke test if behavior changed.

## End-of-Day SOP

Goal:

- leave a clear handoff
- preserve unresolved risks and next actions

Checklist:

1. Collect completed work, open issues, and next actions.
2. Run `scripts/mac/codex-bridge-daily-report.sh`.
3. Save or share the Markdown report.
4. Record any blocked or risky item that still needs human review.

## Artifact Review SOP

When Gemini automation is involved, review these files under `storage/gemini_runs/`:

- `<run_id>-job.json`
- `<run_id>-gemini-output.json`
- `<run_id>-plan.json`
- `<run_id>-exec-results.json`
- `<run_id>-timing.json`
- `<run_id>-final.json`

Use them to answer:

- what the router generated
- what Gemini actually returned
- what commands were executed
- whether the run timed out or was interrupted
- how long the model and execution stages took
