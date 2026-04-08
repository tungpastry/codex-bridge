# Tutorial: Ops Incident With Gemini Auto Runner

This tutorial walks through a low-risk incident workflow where the router chooses the Gemini path.

## Goal

Fetch logs, summarize the issue, let Gemini propose safe commands, and keep an audit trail of what happened.

## Example Scenario

You want to inspect a service on `UbuntuServer` without jumping straight into ad hoc shell work.

## Step 1: Triage the service logs

```bash
./scripts/mac/codex-bridge-triage-log.sh cron.service
```

Review the JSON response:

- `symptom`
- `likely_cause`
- `important_lines`
- `recommended_tool`
- `next_step`

## Step 2: Let the router choose the route

If the issue looks safe for automation, dispatch the task:

```bash
./scripts/mac/codex-bridge-auto.sh task \
  "Inspect codex-bridge service health" \
  "codex-bridge" \
  ./context.txt
```

If the route is `gemini`, the Mac runner will:

1. receive a `gemini_job`
2. call Gemini CLI headless
3. extract plan JSON
4. validate command IDs
5. execute safe commands
6. print final JSON with timing data

## Step 3: Review the artifacts

Look under `storage/gemini_runs/` for the run artifacts:

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

This makes it clear whether the slow part was Gemini headless itself or the safe execution stage.

## Step 5: Stop if the route becomes human

If the router or runner blocks the task:

- do not bypass the safe command flow
- do not inject arbitrary destructive shell
- review the `block_reason` and escalate manually
