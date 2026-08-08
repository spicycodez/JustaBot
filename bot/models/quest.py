"""Quest and UserQuest document models."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from beanie import Document
from pydantic import Field


class Quest(Document):
    """Template for a quest (daily, weekly, seasonal, etc.)."""

    quest_id: str = Field(..., unique=True)
    title: str
    description: str
    quest_type: str  # e.g. "daily", "weekly", "seasonal"
    target: int
    target_type: str  # e.g. "messages", "replies", "invites"
    reward_xp: int
    reward_coins: int
    reward_items: List[str] = Field(default_factory=list)
    difficulty: str
    season: Optional[int] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "quests"


class UserQuest(Document):
    """Tracks a user's progress on a specific quest."""

    user_id: int = Field(..., index=True)
    quest_id: str = Field(..., index=True)
    progress: int = Field(default=0)
    target: int
    is_completed: bool = Field(default=False)
    completed_at: Optional[datetime] = None
    claimed: bool = Field(default=False)
    assigned_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "user_quests"
