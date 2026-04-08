# Contributing

Thanks for contributing to `codex-bridge`.

## What This Project Optimizes For

- practical operator workflows
- clear routing between coding, ops, and human escalation
- simple deployment
- safe automation boundaries
- documentation that matches real behavior

## Development Setup

```bash
git clone git@github.com:tungpastry/codex-bridge.git
cd codex-bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Run the app:

```bash
./scripts/run_dev.sh
```

## Test Before You Open a PR

Minimum checks:

```bash
./.venv/bin/python -m unittest tests.test_router
./scripts/smoke_test.sh
find scripts -type f -name '*.sh' -print0 | xargs -0 -n1 bash -n
```

## Pull Request Guidelines

- keep changes scoped
- preserve the `codex`, `gemini`, `human`, and `local` route model
- do not add UI automation for Codex App
- do not replace the safe Gemini command model with arbitrary shell execution
- update docs when behavior changes
- include operational impact in the PR description if the change affects scripts or deployment

## Commit Style

Short, direct commit messages are preferred. Examples:

- `Add Gemini timing transparency`
- `Improve dispatch docs and deployment notes`
- `Tighten safe command validation`

## Reporting Issues

When filing an issue, include:

- what you tried
- expected behavior
- actual behavior
- relevant route, script, or endpoint
- logs or artifact names if Gemini auto-run was involved

## Security

Do not open public issues with secrets, private keys, production tokens, or sensitive logs. For security-sensitive concerns, contact the maintainer directly.
