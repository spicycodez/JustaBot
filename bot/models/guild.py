"""Guild document model."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from beanie import Document
from pydantic import Field


class Guild(Document):
    """Represents a player guild."""

    name: str = Field(..., index=True)
    tag: str = Field(..., unique=True)
    owner_id: int
    description: Optional[str] = None
    members: List[int] = Field(default_factory=list)

    # ── Stats ─────────────────────────────────────────────────────────────
    total_xp: int = Field(default=0)
    coins: int = Field(default=0)
    wins: int = Field(default=0)
    losses: int = Field(default=0)
    rank: int = Field(default=0)
    level: int = Field(default=1)

    # ── Cosmetics / Meta ──────────────────────────────────────────────────
    emblem: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

    class Settings:
        name = "guilds"
