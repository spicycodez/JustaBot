"""Achievement document model."""

from __future__ import annotations

from typing import Optional

from beanie import Document
from pydantic import Field


class Achievement(Document):
    """Defines an achievement that users can unlock."""

    achievement_id: str = Field(..., unique=True)
    title: str
    description: str
    icon: str
    category: str
    condition_type: str  # e.g. "total_messages", "level_reached"
    condition_value: int
    reward_xp: int = Field(default=0)
    reward_coins: int = Field(default=0)
    reward_title: Optional[str] = None
    reward_badge: Optional[str] = None
    is_secret: bool = Field(default=False)

    class Settings:
        name = "achievements"
