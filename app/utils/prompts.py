from __future__ import annotations

from pathlib import Path


def load_prompt(prompts_dir: Path, name: str) -> str:
    path = prompts_dir / name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def render_prompt(template: str, **kwargs) -> str:
    if not template:
        return ""
    return template.format(**kwargs)
