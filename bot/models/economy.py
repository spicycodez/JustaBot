"""Economy-related document models: LootBox, ShopItem, InventoryItem."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from beanie import Document
from pydantic import Field


class LootBox(Document):
    """A loot box that can be opened for random rewards."""

    box_id: str = Field(..., unique=True)
    rarity: str  # e.g. "common", "rare", "epic", "legendary"
    name: str
    description: str
    icon: str
    possible_rewards: List[Dict]  # [{"type": ..., "item": ..., "amount": ..., "chance": ...}]

    class Settings:
        name = "loot_boxes"


class ShopItem(Document):
    """An item available in the shop."""

    item_id: str = Field(..., unique=True)
    name: str
    description: str
    category: str
    price: int
    currency: str = Field(default="coins")  # "coins" | "gems"
    rarity: Optional[str] = None
    duration: Optional[int] = None  # duration in seconds, if applicable
    effect: Dict = Field(default_factory=dict)

    class Settings:
        name = "shop_items"


class InventoryItem(Document):
    """An item held by a user."""

    user_id: int = Field(..., index=True)
    item_id: str = Field(..., index=True)
    item_name: str
    quantity: int = Field(default=1)
    acquired_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_active: bool = Field(default=True)

    class Settings:
        name = "inventory_items"
