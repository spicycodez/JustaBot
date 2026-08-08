"""Season document model."""

from __future__ import annotations

from datetime import date
from typing import Dict, List

from beanie import Document
from pydantic import Field


class Season(Document):
    """Represents a competitive season."""

    season_number: int = Field(..., unique=True, index=True)
    start_date: date
    end_date: date
    is_active: bool = Field(default=True)
    rewards_distributed: bool = Field(default=False)
    top_users: List[Dict] = Field(default_factory=list)
    top_guilds: List[Dict] = Field(default_factory=list)

    class Settings:
        name = "seasons"
