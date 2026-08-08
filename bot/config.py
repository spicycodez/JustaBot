"""ChatQuest configuration via pydantic-settings."""

from __future__ import annotations

from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ── Telegram ──────────────────────────────────────────────────────────
    BOT_TOKEN: str = ""
    BOT_USERNAME: str = ""

    # ── MongoDB ───────────────────────────────────────────────────────────
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "chatquest"

    # ── Redis ─────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""

    # ── Admin ─────────────────────────────────────────────────────────────
    ADMIN_IDS: List[int] = []

    # ── Gameplay ──────────────────────────────────────────────────────────
    XP_COOLDOWN: int = 20
    ANTI_SPAM_THRESHOLD: int = 3
    ANTI_SPAM_FREEZE_1: int = 300
    ANTI_SPAM_FREEZE_2: int = 600
    ANTI_SPAM_FREEZE_3: int = 1800
    MAX_DAILY_THANKS: int = 5

    # ── Referral ──────────────────────────────────────────────────────────
    REFERRAL_MIN_ACCOUNT_AGE_DAYS: int = 7

    # ── Seasons ───────────────────────────────────────────────────────────
    SEASON_DURATION_DAYS: int = 30

    # ── App ───────────────────────────────────────────────────────────────
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        """Parse comma-separated ADMIN_IDS from env string to list[int]."""
        if isinstance(v, list):
            return [int(i) for i in v]
        if isinstance(v, str) and v.strip():
            return [int(i.strip()) for i in v.split(",") if i.strip()]
        return []


# Singleton instance
settings = Settings()
