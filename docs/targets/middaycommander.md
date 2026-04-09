# MiddayCommander Integration

This document captures how `MiddayCommander` uses `codex-bridge` without turning the target repo into the center of the core architecture docs.

Related docs:

- [README](../../README.md)
- [Workflow](../workflow.md)
- [SOP](../sop.md)
- [Vietnamese version](./middaycommander-vi.md)

## Why MiddayCommander Uses Codex Bridge

`MiddayCommander` uses `codex-bridge` for:

- router deployment wrappers
- multi-node health checks
- operator morning checks
- release preparation and promotion helpers
- internal automation that should not live in the product repo

The application code still belongs in the `MiddayCommander` repo. `codex-bridge` hosts the internal routing and operator layer around it.

## Relevant Scripts

MiddayCommander-specific scripts currently include:

- `scripts/mac/middaycommander-deploy-router.sh`
- `scripts/mac/middaycommander-health.sh`
- `scripts/mac/middaycommander-morning-check.sh`
- `scripts/mac/middaycommander-release.sh`

## Deploy Wrapper

`middaycommander-deploy-router.sh` is used to refresh the router deployment on `UbuntuDesktop`.

Typical responsibilities:

- sync the `codex-bridge` source tree
- avoid syncing hidden macOS sidecar files
- refresh the remote Python environment as needed
- leave restart or post-deploy verification clear for the operator

## Health Wrapper

`middaycommander-health.sh` gives a target-aware health view across the three-node setup.

It is useful for:

- router visibility
- runtime node visibility
- target repo state
- release visibility on UbuntuServer

## Morning Check Wrapper

`middaycommander-morning-check.sh` produces a timestamped Markdown handoff report tailored to the MiddayCommander environment.

Use it when:

- you want a repeatable morning health report
- you need a short operator handoff artifact
- you want target-specific status in one place

## Release Flow

`middaycommander-release.sh` is the target-specific release helper. It supports:

- dry-run validation
- build preparation
- GitHub release publishing
- promotion of the Linux artifact to the managed release directory

This flow is target-specific and intentionally not part of the generic `codex-bridge` core workflow docs.

## Operational Notes

- Keep target-specific logic in `docs/targets/` and target wrappers, not in the core architecture docs.
- Keep target repo code and business logic in the target repo.
- Use `codex-bridge` profiles and prompt hints only to improve routing and safe automation, not to bypass safety rules.
