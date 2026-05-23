"""
Configuration loader — reads config.yaml and environment variables.

Priority (highest to lowest):
  1. Environment variables (uppercase, underscores)
  2. config.yaml values
  3. Built-in defaults
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

# ─── Find config.yaml relative to this file ─────────────────────
_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def _load_yaml() -> dict[str, Any]:
    """Load config.yaml, returning empty dict if absent or invalid."""
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


_YAML: dict[str, Any] = _load_yaml()


# ─── Pydantic settings with env-var overrides ─────────────────
class Settings(BaseSettings):
    """Top-level settings, populated from env vars (prefixed SCAPERS_)."""

    model_config = SettingsConfigDict(
        env_prefix="SCAPERS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API keys
    apollo_api_key: str = ""
    hunter_api_key: str = ""

    # Output
    output_dir: str = "./output"
    default_format: str = "csv"

    # Rate limiting
    default_delay: float = 2.0
    max_retries: int = 3

    # Logging
    log_level: str = "INFO"

    # HTTP
    http_timeout: int = 15
    verify_ssl: bool = True

    # Proxy
    http_proxy: str = ""
    https_proxy: str = ""

    # User agents (comma-separated in env, list in yaml)
    user_agents: list[str] = []


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return cached Settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
        # If user_agents not set via env, pull from yaml
        if not _settings.user_agents:
            yaml_agents = _YAML.get("user_agents", [])
            if yaml_agents:
                _settings.user_agents = yaml_agents
    return _settings


def get_rate_limit(scraper_name: str) -> int:
    """Return requests-per-minute limit for a scraper."""
    limits = _YAML.get("rate_limits", {})
    return limits.get(scraper_name, 60)


def get_delay(scraper_name: str) -> float:
    """Return delay (seconds) between requests for a scraper."""
    delays = _YAML.get("delays", {})
    defaults = _YAML.get("delays", {}).get("default", 2.0)
    return delays.get(scraper_name, delays.get("default", defaults))


def get_http_timeout() -> int:
    """Return HTTP timeout in seconds."""
    return get_settings().http_timeout


def get_max_retries() -> int:
    """Return max retry attempts."""
    return get_settings().max_retries


def get_user_agents() -> list[str]:
    """Return User-Agent rotation pool."""
    return get_settings().user_agents or [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ]


def get_log_level() -> str:
    """Return log level."""
    return get_settings().log_level


def get_output_dir() -> Path:
    """Return resolved output directory."""
    return Path(get_settings().output_dir).expanduser().resolve()


def get_yaml_value(*keys: str, default: Any = None) -> Any:
    """Traverse YAML nested dict by keys, return default if not found."""
    val: Any = _YAML
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            return default
        if val is None:
            return default
    return val
