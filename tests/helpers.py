from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from fastapi.testclient import TestClient

from app.core.settings import get_settings
from app.main import app


ROOT = Path(__file__).resolve().parents[1]
ENV_KEYS = (
    "PROMPTS_DIR",
    "STORAGE_DIR",
    "RUN_INDEX_DB_PATH",
    "PROFILES_DIR",
    "CODEX_BRIDGE_INTERNAL_API_TOKEN",
)


@contextmanager
def temporary_settings_env() -> Iterator[Path]:
    original = {key: os.environ.get(key) for key in ENV_KEYS}
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        os.environ["PROMPTS_DIR"] = str(ROOT / "prompts")
        os.environ["STORAGE_DIR"] = str(temp_root / "storage")
        os.environ["RUN_INDEX_DB_PATH"] = str(temp_root / "storage" / "index" / "runs.db")
        os.environ["PROFILES_DIR"] = str(ROOT / "app" / "profiles")
        os.environ["CODEX_BRIDGE_INTERNAL_API_TOKEN"] = "test-internal-token"
        get_settings.cache_clear()
        try:
            yield temp_root
        finally:
            get_settings.cache_clear()
            for key, value in original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            get_settings.cache_clear()


@contextmanager
def temporary_client() -> Iterator[tuple[TestClient, Path]]:
    with temporary_settings_env() as temp_root:
        with TestClient(app) as client:
            yield client, temp_root
