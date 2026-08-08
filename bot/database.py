"""MongoDB / Beanie initialisation."""

from __future__ import annotations

import beanie
from motor.motor_asyncio import AsyncIOMotorClient

from bot.config import settings
from bot.models import (  # noqa: F401 – required so Beanie registers documents
    Achievement,
    ChatSettings,
    Event,
    Guild,
    GuildBattle,
    InventoryItem,
    LootBox,
    Quest,
    Referral,
    Season,
    ShopItem,
    User,
    UserQuest,
)


async def init_db() -> AsyncIOMotorClient:
    """Connect to MongoDB and initialise Beanie document models.

    Returns the motor client so callers can close it on shutdown.
    """
    client: AsyncIOMotorClient = AsyncIOMotorClient(settings.MONGODB_URI)

    await beanie.init_beanie(
        database=client[settings.MONGODB_DB_NAME],
        document_models=[
            User,
            Guild,
            Quest,
            UserQuest,
            Achievement,
            Event,
            GuildBattle,
            Season,
            LootBox,
            ShopItem,
            InventoryItem,
            Referral,
            ChatSettings,
        ],
    )

    return client
