# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-04-08

Initial practical release of `codex-bridge`.

Added:

- FastAPI router with health, classify, summarize, compress, brief, report, and dispatch endpoints
- multilingual heuristic routing for `codex`, `gemini`, `human`, and `local`
- Gemini CLI auto-run path with safe command validation
- Mac operator scripts for health, log triage, diff summary, daily reporting, dispatch, and automation
- systemd unit for UbuntuDesktop deployment
- request and response snapshot storage
- Gemini timing transparency with `run_id`, `job_id`, `timing_summary`, and persisted timing artifacts
- architecture, workflow, SOP, API, deployment, troubleshooting, and tutorial docs
