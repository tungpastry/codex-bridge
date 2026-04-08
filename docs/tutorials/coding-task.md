# Tutorial: Coding Task to Codex Brief

This tutorial walks through the intended v1 path for coding work.

## Goal

Turn a noisy bug report into a brief that is clean enough to paste into Codex App.

## Example Scenario

You have a `MiddayCommander` bug:

- title: `Transfer retry panic`
- context: `Go test fails with panic after remote retry exhaustion`
- constraint: `keep the patch small`

## Step 1: Save the raw context

Create a text file with the issue details:

```bash
cat > /tmp/middaycommander-panic.txt <<'EOF'
Go test fails with panic after remote retry exhaustion in the transfer queue.
The panic appears after retries are exhausted.
Keep the patch small and avoid redesigning the retry engine.
EOF
```

## Step 2: Generate the brief

```bash
./scripts/mac/codex-bridge-make-brief.sh \
  "Fix MiddayCommander transfer retry panic" \
  "MiddayCommander" \
  /tmp/middaycommander-panic.txt
```

## Step 3: Review the generated Markdown

The output should include:

- `Task`
- `Repo`
- `Task Type`
- `Goal`
- `Context`
- `Constraints`
- `Acceptance Criteria`
- `Likely Files`
- `Notes`

## Step 4: Paste into Codex App

Paste the generated Markdown into Codex App and continue the implementation workflow there.

## Optional Step: Use Dispatch Instead

If you want routing and artifact generation in one call:

```bash
./scripts/mac/codex-bridge-auto.sh task \
  "Fix MiddayCommander transfer retry panic" \
  "MiddayCommander" \
  /tmp/middaycommander-panic.txt
```

If the route is `codex`, the script prints the final brief. If the route is `human`, stop and review the escalation reason.
