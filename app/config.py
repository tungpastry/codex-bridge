from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _fallback_runtime_path(configured: Path, local_name: str, must_exist: bool = False) -> Path:
    project_path = _default_project_root() / local_name
    candidate = configured.expanduser()

    if candidate == project_path:
        return candidate

    if must_exist:
        return candidate if candidate.exists() else project_path

    try:
        candidate.mkdir(parents=True, exist_ok=True)
    except OSError:
        project_path.mkdir(parents=True, exist_ok=True)
        return project_path
    return candidate


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        enable_decoding=False,
    )

    app_name: str = Field(default="codex-bridge", validation_alias="APP_NAME")
    app_env: str = Field(default="dev", validation_alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", validation_alias="APP_HOST")
    app_port: int = Field(default=8787, validation_alias="APP_PORT")

    llm_backend: str = Field(default="ollama", validation_alias="LLM_BACKEND")
    llm_base_url: str = Field(default="http://127.0.0.1:11434", validation_alias="LLM_BASE_URL")
    llm_model: str = Field(default="gemma3:1b-it-qat", validation_alias="LLM_MODEL")
    llm_timeout_seconds: float = Field(default=120.0, validation_alias="LLM_TIMEOUT_SECONDS")

    prompts_dir: Path = Field(
        default_factory=lambda: _default_project_root() / "prompts",
        validation_alias="PROMPTS_DIR",
    )
    storage_dir: Path = Field(
        default_factory=lambda: _default_project_root() / "storage",
        validation_alias="STORAGE_DIR",
    )
    cors_allow_origins_raw: List[str] = Field(
        default_factory=lambda: ["http://localhost", "http://127.0.0.1"],
        validation_alias="CORS_ALLOW_ORIGINS_RAW",
    )
    allowed_restart_services_raw: List[str] = Field(
        default_factory=lambda: ["codex-bridge", "postgresql", "nginx"],
        validation_alias="ALLOWED_RESTART_SERVICES_RAW",
    )

    @field_validator("prompts_dir", "storage_dir", mode="before")
    @classmethod
    def _coerce_path(cls, value):
        return Path(value).expanduser() if value is not None else value

    @field_validator("cors_allow_origins_raw", "allowed_restart_services_raw", mode="before")
    @classmethod
    def _parse_csv(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    def ensure_runtime_dirs(self) -> None:
        self.prompts_dir = _fallback_runtime_path(self.prompts_dir, "prompts", must_exist=True)
        self.storage_dir = _fallback_runtime_path(self.storage_dir, "storage")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        for name in ("cache", "requests", "responses", "reports", "gemini_runs"):
            (self.storage_dir / name).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_dirs()
    return settings
