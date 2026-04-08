# SOP

This document turns the main workflows into operator checklists that are easy to repeat.

## Morning SOP

Goal:

- confirm the router is reachable
- confirm key services are alive
- catch obvious incidents early

Checklist:

1. Run `scripts/mac/middaycommander-health.sh`.
2. Run `scripts/mac/middaycommander-morning-check.sh`.
3. Review the Markdown report under `storage/reports/`.
4. Review inactive, failed, or restarting services on `UbuntuDesktop` or `UbuntuServer`.
5. Check whether router health, LAN reachability, or the MiddayCommander server repo state look abnormal.
6. Escalate risky production findings to a human before any change is made.

Expected output:

- Markdown report with `Router`, `UbuntuDesktop`, `UbuntuServer`, `MiddayCommander Repo`, `MiddayCommander Release`, `Open Issues`, and `Next Actions`
- clear branch/head/worktree visibility for the MiddayCommander repo on `192.168.1.30`
- clear release-root/current-version visibility for the promoted MiddayCommander binary on `192.168.1.30`
- obvious operator next steps

## Release SOP

Goal:

- produce a repeatable tagged release for MiddayCommander
- publish it to GitHub
- promote the Linux server binary without manual copy/paste deploy steps

Checklist:

1. Confirm the local MiddayCommander worktree is clean.
2. Confirm the release tag is annotated and points to `HEAD`.
3. Confirm `gh` and `goreleaser` are installed on the Mac mini.
4. Run `scripts/mac/middaycommander-release.sh --tag <tag> --dry-run`.
5. Run `scripts/mac/middaycommander-release.sh --tag <tag>`.
6. Run `scripts/mac/middaycommander-health.sh` to confirm repo health and promoted release health.
7. Save or review `storage/releases/<tag>/summary.json`, `publish.json`, and `promote.json` for handoff.

Expected output:

- a GitHub release in `tungpastry/MiddayCommander`
- a promoted server release under `/home/nexus/releases/middaycommander/releases/<tag>/`
- `current -> releases/<tag>` on UbuntuServer
- successful `current/mdc --version`

Stop conditions:

- dirty repo
- missing or lightweight tag
- missing `gh` or `goreleaser`
- GitHub release already exists
- target server release directory already exists

## Build SOP

Goal:

- keep code tasks clean, scoped, and reviewable

Checklist:

1. Gather the issue title, repo, and raw context.
2. Run `scripts/mac/codex-bridge-dispatch.sh task ...` or `scripts/mac/codex-bridge-make-brief.sh ...`.
3. If the route is `codex`, copy the generated brief into Codex App.
4. Keep the implementation scoped to the stated goal and constraints.
5. Run local tests, smoke checks, or relevant validation commands.
6. Review the patch before commit.

MiddayCommander note:

- build/test/commit work stays in the MiddayCommander repo
- new deploy and health runbooks for that repo now live in `codex-bridge`

Stop conditions:

- if the task is actually an ops issue, switch to the incident flow
- if the task includes risky production signals, stop and escalate

## Incident SOP

Goal:

- inspect the system safely
- avoid destructive improvisation during pressure

Checklist:

1. Run `scripts/mac/codex-bridge-triage-log.sh <service>`.
2. Review the returned summary and recommended tool.
3. If safe, run `scripts/mac/codex-bridge-auto.sh log ...` or dispatch a Gemini job through the push path.
4. Review the executed commands and the final Markdown summary in `storage/gemini_runs/`.
5. Review timing information if Gemini latency felt slow or ambiguous.
6. Stop immediately if the route becomes `human` or the plan is blocked.

What not to do:

- do not bypass the safe command layer with ad hoc destructive shell
- do not treat production auth, firewall, or schema changes as routine auto-runs

## End-of-Day SOP

Goal:

- leave a clear handoff
- preserve unresolved risks and next actions

Checklist:

1. Collect completed work, open issues, and next actions.
2. Run `scripts/mac/codex-bridge-daily-report.sh`.
3. Save or share the Markdown report.
4. Record any risky or blocked item that still needs human review.
5. Confirm the next operator can tell what is done and what is still pending.

## Artifact Review SOP

When Gemini auto-run is involved, check these files under `storage/gemini_runs/`:

- `<run_id>-job.json`
- `<run_id>-gemini-output.json`
- `<run_id>-plan.json`
- `<run_id>-exec-results.json`
- `<run_id>-timing.json`
- `<run_id>-final.json`

Use them to answer:

- what job the router generated
- what Gemini actually returned
- what commands were executed
- whether the run timed out or was interrupted
- how long the headless stage and total pipeline took
