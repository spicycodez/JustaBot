"""ChatQuest Beanie document models.

All models are re-exported here so that ``bot.database`` can import them
in one shot for Beanie initialisation.
"""

from bot.models.user import User
from bot.models.guild import Guild
from bot.models.quest import Quest, UserQuest
from bot.models.achievement import Achievement
from bot.models.event import Event
from bot.models.battle import GuildBattle
from bot.models.season import Season
from bot.models.economy import LootBox, ShopItem, InventoryItem
from bot.models.referral import Referral
from bot.models.settings import ChatSettings

__all__ = [
    "User",
    "Guild",
    "Quest",
    "UserQuest",
    "Achievement",
    "Event",
    "GuildBattle",
    "Season",
    "LootBox",
    "ShopItem",
    "InventoryItem",
    "Referral",
    "ChatSettings",
]
