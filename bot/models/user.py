"""User document model."""

from __future__ import annotations

import secrets
from datetime import date, datetime
from typing import Dict, List, Optional

from beanie import Document
from bson import ObjectId
from pydantic import Field


class User(Document):
    """Represents a Telegram user in the RPG system."""

    telegram_id: int = Field(..., index=True, unique=True)
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    chat_id: int = Field(..., index=True)

    # ── Progression ───────────────────────────────────────────────────────
    level: int = Field(default=1)
    xp: int = Field(default=0)
    total_xp: int = Field(default=0)
    coins: int = Field(default=0)
    gems: int = Field(default=0)
    tickets: int = Field(default=0)
    rank: str = Field(default="Newcomer")
    title: Optional[str] = None

    # ── Guild ─────────────────────────────────────────────────────────────
    guild_id: Optional[ObjectId] = None
    guild_name: Optional[str] = None

    # ── Activity ──────────────────────────────────────────────────────────
    streak: int = Field(default=0)
    last_active: Optional[datetime] = None
    last_daily_claim: Optional[date] = None
    reputation: int = Field(default=0)
    total_messages: int = Field(default=0)
    total_replies: int = Field(default=0)
    total_invites: int = Field(default=0)

    # ── Referral ──────────────────────────────────────────────────────────
    referral_code: str = Field(default_factory=lambda: secrets.token_urlsafe(8), unique=True)
    referred_by: Optional[int] = None

    # ── Extras ────────────────────────────────────────────────────────────
    achievements: List[str] = Field(default_factory=list)
    temporary_powers: List[Dict] = Field(default_factory=list)
    xp_frozen_until: Optional[datetime] = None

    # ── Anti-spam ─────────────────────────────────────────────────────────
    spam_count: int = Field(default=0)
    last_message_text: Optional[str] = None
    last_message_time: Optional[datetime] = None

    # ── Season ────────────────────────────────────────────────────────────
    season_xp: int = Field(default=0)
    season_coins: int = Field(default=0)

    # ── Meta ──────────────────────────────────────────────────────────────
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    is_banned: bool = Field(default=False)

    class Settings:
        name = "users"
