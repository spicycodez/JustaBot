"""ChatSettings document model."""

from __future__ import annotations

from typing import Dict, List, Optional

from beanie import Document
from pydantic import Field


class ChatSettings(Document):
    """Per-chat configuration for the bot."""

    chat_id: int = Field(..., unique=True, index=True)
    is_enabled: bool = Field(default=True)
    xp_enabled: bool = Field(default=True)
    quests_enabled: bool = Field(default=True)
    guilds_enabled: bool = Field(default=True)
    events_enabled: bool = Field(default=True)
    min_message_length: int = Field(default=10)
    xp_multiplier: float = Field(default=1.0)
    allowed_guilds: List[str] = Field(default_factory=list)
    custom_rank_titles: Dict[str, str] = Field(default_factory=dict)
    log_channel_id: Optional[int] = None
    admin_channel_id: Optional[int] = None

    class Settings:
        name = "chat_settings"
