# Tutorial: Ops Incident with the Gemini Auto Runner

This tutorial shows a low-risk incident workflow where the router chooses the Gemini path.

Related docs:

- [Workflow](../workflow.md)
- [Troubleshooting](../troubleshooting.md)
- [Vietnamese version](./ops-incident-vi.md)

## Goal

Inspect a service safely, let Gemini propose typed commands, and keep an audit trail of what happened.

## Example Scenario

You want to inspect a service on `UbuntuDesktop` or `UbuntuServer` without jumping into ad hoc shell work.

## Step 1: Triage the logs

```bash
./scripts/mac/codex-bridge-triage-log.sh cron.service
```

Review:

- `symptom`
- `likely_cause`
- `recommended_tool`
- `next_step`

## Step 2: Let dispatch pick the route

```bash
./scripts/mac/codex-bridge-dispatch.sh \
  task \
  "Inspect service health" \
  codex-bridge \
  /path/to/context.txt
```

If the route is `gemini`, the Mac runner will:

1. receive a `gemini_job`
2. call Gemini CLI headless
3. extract plan JSON
4. validate command IDs and hosts
5. execute safe commands
6. print final JSON with timing data

## Step 3: Review the artifacts

Look under `storage/gemini_runs/` for:

- `<run_id>-job.json`
- `<run_id>-gemini-output.json`
- `<run_id>-plan.json`
- `<run_id>-exec-results.json`
- `<run_id>-timing.json`
- `<run_id>-final.json`

## Step 4: Read the timing output

Focus on:

- `timing_summary`
- `timing.gemini_cli_duration_ms`
- `timing.exec_duration_ms`
- `timing.total_duration_ms`

## Step 5: Stop if the route becomes human

If the router or runner blocks the task:

- do not bypass the safe command layer
- do not inject arbitrary destructive shell
- review `block_reason` and escalate manually
