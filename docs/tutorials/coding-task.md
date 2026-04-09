# Tutorial: Coding Task to Codex Brief

This tutorial shows the intended path for implementation-heavy work.

Related docs:

- [Workflow](../workflow.md)
- [API Reference](../api-reference.md)
- [Vietnamese version](./coding-task-vi.md)

## Goal

Turn a noisy coding task into a clean brief for Codex App.

## Example Scenario

You have a bug in `ExampleService`:

- title: `Retry loop panic`
- context: `Tests fail after retry exhaustion in the transfer path`
- constraint: `keep the patch small`

## Step 1: Save the raw context

```bash
cat > /tmp/example-retry-panic.txt <<'EOF'
Tests fail after retry exhaustion in the transfer path.
The panic appears after retries are exhausted.
Keep the patch small and avoid redesigning the retry logic.
EOF
```

## Step 2: Generate the brief

```bash
./scripts/mac/codex-bridge-make-brief.sh \
  "Fix ExampleService retry panic" \
  "ExampleService" \
  /tmp/example-retry-panic.txt
```

## Step 3: Review the generated Markdown

The output should include:

- task summary
- repo
- task type
- goal
- constraints
- acceptance criteria
- likely files

## Step 4: Paste into Codex App

Paste the generated Markdown into Codex App and continue the implementation manually.

## Optional: Use Dispatch Instead

```bash
./scripts/mac/codex-bridge-dispatch.sh \
  task \
  "Fix ExampleService retry panic" \
  ExampleService \
  /tmp/example-retry-panic.txt
```

If the route is `codex`, use `codex_brief_markdown`. If the route is `human`, stop and review the escalation reason.
