# Upgrade Blueprint v1

This document summarizes what the production upgrade changed in the shipped system. It is a completed architecture note, not a future plan.

Related docs:

- [Architecture](./architecture.md)
- [API Reference](./api-reference.md)
- [Deployment](./deployment.md)
- [Vietnamese version](./upgrade-blueprint-v1-vi.md)

## Goals Completed

The v1 production upgrade moved `codex-bridge` from a lightweight router prototype toward a more production-ready internal platform while preserving the original philosophy:

- heuristic-first routing
- fail-closed safety
- no Codex App UI automation
- no arbitrary shell execution from Gemini
- observable runs with persisted artifacts

## Major Changes Delivered

### 1. Production Package Structure

The app is now organized into clear packages for API routes, policy, builders, execution, artifacts, profiles, runtime bootstrap, and run index management.

### 2. SQLite Run Index

The router now owns a SQLite run index with migrations and query APIs. This adds:

- persistent run summaries
- command and rule history
- artifact indexing
- admin metrics

### 3. Decision Trace

Heuristic decisions are now explainable through `decision_trace` in classify, log, diff, and dispatch responses.

### 4. Dispatch Persistence

`dispatch` now creates `run_id`, stores request and response snapshots, indexes rules, and tracks generated artifacts.

### 5. Typed Execution Model

Gemini plans are now constrained to typed command specifications instead of free-form shell instructions.

### 6. Internal Execution Callback

The Mac runner updates the router-side run index through an authenticated internal callback so execution results remain observable from the router host.

### 7. Runs and Metrics APIs

The platform now exposes:

- `/v1/runs`
- `/v1/runs/{run_id}`
- `/v1/runs/{run_id}/artifacts`
- `/v1/admin/metrics`
- `/health?depth=full`

### 8. Profiles and Preferred Hosts

YAML profiles now provide minimal repo-specific hints. They can guide likely files, prompt hints, default safe services, and preferred command hosts.

## Design Choices Preserved

The upgrade did not change these core boundaries:

- Codex App remains a manual implementation workflow
- Gemini remains inside a strict safe command boundary
- risky work still escalates to `human`
- the system is still intentionally lightweight and local-first

## Operational Notes

- startup now logs migration details for the run index
- run artifacts on disk remain the full audit trail
- SQLite is the query layer, not a replacement for filesystem artifacts
- timing telemetry distinguishes model latency from execution latency

## Known Limits Still Present

- no queue or worker fleet
- no distributed job orchestration
- no browser automation
- no AppleScript
- no attempt to auto-resolve ambiguous or risky production intent
