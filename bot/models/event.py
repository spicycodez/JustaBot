"""Event document model."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from beanie import Document
from pydantic import Field


class Event(Document):
    """A community event (tournament, boss raid, etc.)."""

    event_id: str = Field(..., unique=True)
    title: str
    description: str
    event_type: str  # e.g. "tournament", "boss_raid"
    chat_id: int
    host_id: int
    participants: List[int] = Field(default_factory=list)
    status: str = Field(default="upcoming")  # upcoming | active | completed | cancelled
    reward_xp_participant: int
    reward_xp_host: int
    reward_coins_participant: int = Field(default=0)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "events"
