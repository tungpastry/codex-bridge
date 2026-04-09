from __future__ import annotations

from pathlib import Path

import yaml

from app.schemas.profile import ProfileDefinition


def load_profiles(profiles_dir: Path) -> dict[str, ProfileDefinition]:
    profiles: dict[str, ProfileDefinition] = {}
    if not profiles_dir.exists():
        return profiles
    for path in sorted(profiles_dir.glob("*.yaml")):
        if path.name.startswith("."):
            continue
        profile = ProfileDefinition.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
        profiles[profile.repo_name] = profile
    return profiles


def resolve_profile(repo_name: str, profiles: dict[str, ProfileDefinition]) -> ProfileDefinition | None:
    if not repo_name:
        return None
    for key, profile in profiles.items():
        if key.lower() == repo_name.lower():
            return profile
    return None
