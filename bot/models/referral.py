"""Referral document model."""

from __future__ import annotations

from datetime import datetime
from typing import List

from beanie import Document
from pydantic import Field


class Referral(Document):
    """Tracks a referral relationship between two users."""

    referrer_id: int = Field(..., index=True)
    referred_id: int = Field(..., index=True, unique=True)
    referral_code: str
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=False)
    activated_at: datetime | None = None
    rewards_claimed: List[bool] = Field(default_factory=lambda: [False, False, False])

    class Settings:
        name = "referrals"
