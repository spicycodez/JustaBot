"""GuildBattle document model."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from beanie import Document
from bson import ObjectId
from pydantic import Field


class GuildBattle(Document):
    """Represents a battle between two guilds."""

    battle_id: str = Field(..., unique=True)
    guild_a: ObjectId
    guild_b: ObjectId
    guild_a_name: str
    guild_b_name: str
    status: str = Field(default="pending")  # pending | active | completed
    score_a: int = Field(default=0)
    score_b: int = Field(default=0)
    objectives: List[Dict] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    winner: Optional[str] = None  # "guild_a" | "guild_b" | "draw"
    reward_coins: int = Field(default=0)
    reward_xp_boost: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "guild_battles"
