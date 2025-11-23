"""Centralized application settings for CNC Telemetry."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

# Base directory for backend (…/backend)
BACKEND_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BACKEND_DIR / "config.json"


def _get_env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "y", "yes"}


def _load_config_file() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        # Fail-safe: ignore malformed config files
        return {}


_CONFIG = _load_config_file()


def _cfg(name: str, default: str | bool) -> str | bool:
    if name in os.environ:
        return os.environ[name]
    if name in _CONFIG:
        return _CONFIG[name]
    return default


def _cfg_bool(name: str, default: bool) -> bool:
    """Parse boolean-like values from config file safely.

    Accepts real booleans and common string forms ("true", "1", "y", "yes").
    Anything else falls back to `default` semantics.
    """
    if name not in _CONFIG:
        return default

    raw = _CONFIG[name]
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "y", "yes"}
    return bool(raw)


USE_SIMULATION_DATA: bool = _get_env_bool(
    "USE_SIMULATION_DATA",
    _cfg_bool("USE_SIMULATION_DATA", True),
)

MACHINE_ID: str = str(_cfg("MACHINE_ID", "M80-DEMO-01"))
MACHINE_IP: str = str(_cfg("MACHINE_IP", "192.168.1.10"))
API_URL: str = str(_cfg("API_URL", "http://127.0.0.1:8001"))

ENABLE_M80_WORKER: bool = _get_env_bool(
    "ENABLE_M80_WORKER",
    _cfg_bool("ENABLE_M80_WORKER", True),
)
TELEMETRY_POLL_INTERVAL_SEC: float = float(_cfg("TELEMETRY_POLL_INTERVAL_SEC", 1.0))


def _env(key: str, default: str | None = None) -> str | None:
    value = os.getenv(key)
    if value is None:
        return default
    return value


@dataclass(frozen=True)
class Settings:
    """Minimal settings object for pilot deployments."""

    database_url: str = _env(
        "TELEMETRY_DATABASE_URL",
        _env("DATABASE_URL", "sqlite:///./telemetry_beta.db"),
    )
    api_host: str = _env("TELEMETRY_API_HOST", "0.0.0.0") or "0.0.0.0"
    api_port: int = int(_env("TELEMETRY_API_PORT", "8000") or 8000)


settings = Settings()
