# Workflow

This document describes the core generic workflows supported by `codex-bridge`.

Related docs:

- [README](../README.md)
- [Architecture](./architecture.md)
- [Deployment](./deployment.md)
- [SOP](./sop.md)
- [MiddayCommander target docs](./targets/middaycommander.md)
- [Vietnamese version](./workflow-vi.md)

## 1. Coding Work to Codex

Typical use cases:

- feature implementation
- bugfix work
- code review that is likely to result in a patch
- setup work that still requires code changes

Recommended path:

1. gather a task title, repo name, and raw context
2. call `scripts/mac/codex-bridge-dispatch.sh task ...` or `scripts/mac/codex-bridge-make-brief.sh ...`
3. if the route is `codex`, review `codex_brief_markdown`
4. paste the brief into Codex App manually
5. implement and validate the patch in the target repo

Why this route exists:

- coding tasks benefit from clean structured context
- manual implementation and review still stay in the loop
- `codex-bridge` handles routing and context cleanup without pretending code changes are safe to auto-run

Stop conditions:

- if the task becomes a production-risk issue, route to `human`
- if the task is really an ops investigation, reroute to `gemini`

## 2. Safe Ops Investigation with Gemini

Typical use cases:

- service health inspection
- low-risk log review
- port, disk, memory, and uptime checks
- allowlisted service restart when the plan stays safe

Recommended path:

1. summarize the issue with `scripts/mac/codex-bridge-triage-log.sh` or `dispatch`
2. confirm the route is `gemini`
3. let the Mac runner call Gemini CLI headless
4. validate the returned typed plan
5. execute only allowed commands
6. review `final_markdown`, timing, and saved artifacts

What this route is good at:

- recent service inspection
- low-risk operator workflows
- explicit observability through run artifacts and run index entries

Stop conditions:

- the route becomes `human`
- the plan references a forbidden host or command
- the issue involves auth, firewall, schema, secrets, or destructive operations

## 3. Daily Ops and Reporting

Typical use cases:

- morning checks
- lightweight operator reporting
- short handoff summaries
- repeated service visibility

Recommended path:

1. run `scripts/mac/codex-bridge-health.sh`
2. run `scripts/mac/codex-bridge-morning-check.sh`
3. collect completed items, open issues, and next actions
4. run `scripts/mac/codex-bridge-daily-report.sh`

Expected outputs:

- a short health summary
- operator-readable Markdown
- queryable runs and artifacts when dispatch or Gemini automation is involved

## 4. Generic Target Integration Workflow

`codex-bridge` is designed to support target repositories without making them part of the core architecture docs.

The generic integration model is:

1. define a profile with repo hints and preferred command hosts if needed
2. keep application code in the target repo
3. keep internal routing, health wrappers, and ops automation in `codex-bridge`
4. document target-specific deploy and health flows under `docs/targets/`

For a concrete example, see [MiddayCommander target docs](./targets/middaycommander.md).

## Cross-Workflow Notes

These rules stay true in every workflow:

- route choice is explicit
- risky work is blocked instead of improvised
- Codex App stays manual
- Gemini is limited to typed safe command execution
- run artifacts plus the SQLite run index make execution observable
- the router remains heuristic-first rather than model-first
