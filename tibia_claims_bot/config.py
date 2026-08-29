"""Application configuration loaded from environment variables / .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"Environment variable {name} must be an integer, got {raw!r}") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable runtime configuration for the bot."""

    discord_token: str
    channel_id: int
    api_url: str
    poll_interval_seconds: int
    state_file: str
    log_level: str
    embed_color_new: int
    embed_color_removed: int
    embed_color_status: int
    max_events_per_message: int

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            discord_token=_require("DISCORD_TOKEN"),
            channel_id=int(_require("DISCORD_CHANNEL_ID")),
            api_url=os.getenv(
                "TIBIA_CLAIMS_API_URL",
                "https://api.tibiaclaims.com/api/v1/claim-servers/karmeya/board",
            ),
            poll_interval_seconds=_get_int("POLL_INTERVAL_SECONDS", 60),
            state_file=os.getenv("STATE_FILE", "data/last_snapshot.json"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            embed_color_new=0x2ECC71,       # green
            embed_color_removed=0xE74C3C,   # red
            embed_color_status=0xF39C12,    # orange
            max_events_per_message=20,
        )


settings = Settings.load()
