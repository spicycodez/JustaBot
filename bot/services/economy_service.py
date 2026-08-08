import json
import random
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from bot.models.user import User
from bot.models.inventory import Inventory

logger = logging.getLogger(__name__)

_SHOP_DATA: Optional[List[Dict[str, Any]]] = None


ndef _load_shop_items() -> List[Dict[str, Any]]:
    """Load shop items from data/shop_items.json."""
    global _SHOP_DATA
    if _SHOP_DATA is None:
        import os
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "shop_items.json",
        )
        with open(data_path, "r", encoding="utf-8") as f:
            _SHOP_DATA = json.load(f)
    return _SHOP_DATA


def get_shop_items(category: str = "all") -> List[Dict[str, Any]]:
    """
    Get shop items filtered by category.
    Returns a list of item dictionaries.
    """
    items = _load_shop_items()
    if category != "all":
        items = [i for i in items if i["category"] == category]
    return items


def purchase_item(db: Session, user_id: int, item_id: str) -> Dict[str, Any]:
    """
    Purchase a shop item. Checks price, deducts coins, adds to inventory.
    Returns purchase details.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found.")

    # Find item
    all_items = _load_shop_items()
    item_def = None
    for i in all_items:
        if i["item_id"] == item_id:
            item_def = i
            break

    if not item_def:
        raise ValueError(f"Item '{item_id}' not found in shop.")

    # Check price
    price = item_def["price"]
    if user.coins < price:
        raise ValueError(
            f"Not enough coins. Need {price}, have {user.coins}."
        )

    # Deduct coins
    user.coins -= price

    # Add to inventory
    inv_item = Inventory(
        user_id=user_id,
        item_id=item_def["item_id"],
        item_name=item_def["name"],
        category=item_def["category"],
        effect=item_def["effect"],
        rarity=item_def["rarity"],
        quantity=1,
        purchased_at=datetime.utcnow(),
    )
    db.add(inv_item)

    # Apply immediate effects
    _apply_item_effect(user, item_def)

    db.commit()
    db.refresh(inv_item)

    logger.info(f"User {user_id} purchased '{item_def['name']}' for {price} coins")
    return {
        "item_id": item_def["item_id"],
        "item_name": item_def["name"],
        "price_paid": price,
        "remaining_coins": user.coins,
        "effect_applied": item_def["effect"]["type"],
    }


def _apply_item_effect(user: User, item_def: Dict[str, Any]) -> None:
    """Apply an item's effect to the user immediately."""
    effect = item_def.get("effect", {})
    effect_type = effect.get("type")

    if effect_type == "title":
        user.title = effect.get("value")
    elif effect_type == "role_color":
        user.role_color = effect.get("value")
    elif effect_type == "name_effect":
        user.name_effect = effect.get("value")
    elif effect_type == "chat_decoration":
        user.chat_decoration = effect.get("value")
    # Boosts and consumables are handled via use_item


def use_item(db: Session, user_id: int, inventory_item_id: int) -> Dict[str, Any]:
    """
    Activate or consume an inventory item.
    Returns the result of using the item.
    """
    inv_item = (
        db.query(Inventory)
        .filter(Inventory.id == inventory_item_id, Inventory.user_id == user_id)
        .first()
    )
    if not inv_item:
        raise ValueError("Inventory item not found.")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found.")

    effect = inv_item.effect or {}
    effect_type = effect.get("type")
    result = {"item_name": inv_item.item_name, "effect_type": effect_type}

    if effect_type == "xp_multiplier":
        user.xp_boost_active = True
        user.xp_boost_multiplier = effect.get("value", 2)
        user.xp_boost_expires = datetime.utcnow().timestamp() + effect.get("duration", 3600)
        result["multiplier"] = effect.get("value", 2)
        result["duration_seconds"] = effect.get("duration", 3600)
        inv_item.quantity = max(0, inv_item.quantity - 1)

    elif effect_type == "coin_multiplier":
        user.coin_boost_active = True
        user.coin_boost_multiplier = effect.get("value", 2)
        user.coin_boost_expires = datetime.utcnow().timestamp() + effect.get("duration", 7200)
        result["multiplier"] = effect.get("value", 2)
        result["duration_seconds"] = effect.get("duration", 7200)
        inv_item.quantity = max(0, inv_item.quantity - 1)

    elif effect_type == "quest_skip":
        result["skipped"] = effect.get("value", 1)
        inv_item.quantity = max(0, inv_item.quantity - 1)

    elif effect_type == "title":
        user.title = effect.get("value")
        result["title"] = effect.get("value")

    elif effect_type == "role_color":
        user.role_color = effect.get("value")
        result["color"] = effect.get("value")

    elif effect_type == "name_effect":
        user.name_effect = effect.get("value")
        result["effect"] = effect.get("value")

    elif effect_type == "chat_decoration":
        user.chat_decoration = effect.get("value")
        result["decoration"] = effect.get("value")

    else:
        result["message"] = "Item effect applied."

    # Remove if quantity is 0 and not stackable or permanent
    if inv_item.quantity <= 0:
        db.delete(inv_item)

    db.commit()
    logger.info(f"User {user_id} used item '{inv_item.item_name}'")
    return result


def get_user_inventory(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """
    Get all inventory items for a user.
    Returns a list of inventory item dictionaries.
    """
    items = (
        db.query(Inventory)
        .filter(Inventory.user_id == user_id)
        .order_by(Inventory.purchased_at.desc())
        .all()
    )

    return [
        {
            "id": item.id,
            "item_id": item.item_id,
            "item_name": item.item_name,
            "category": item.category,
            "effect": item.effect,
            "rarity": item.rarity,
            "quantity": item.quantity,
            "purchased_at": item.purchased_at.isoformat() if item.purchased_at else None,
        }
        for item in items
    ]


# Loot box reward pools
_LOOT_POOLS = {
    "common": {
        "rewards": [
            {"type": "coins", "amount": 50, "weight": 40},
            {"type": "coins", "amount": 100, "weight": 25},
            {"type": "xp", "amount": 75, "weight": 20},
            {"type": "xp", "amount": 150, "weight": 10},
            {"type": "item", "item_id": "decoration_sparkle", "weight": 5},
        ],
    },
    "rare": {
        "rewards": [
            {"type": "coins", "amount": 300, "weight": 25},
            {"type": "coins", "amount": 500, "weight": 15},
            {"type": "xp", "amount": 400, "weight": 20},
            {"type": "xp", "amount": 800, "weight": 15},
            {"type": "item", "item_id": "name_effect_bold", "weight": 10},
            {"type": "item", "item_id": "loot_box_common", "weight": 10},
            {"type": "badge", "badge": "lucky_opener", "weight": 5},
        ],
    },
}


def open_loot_box(db: Session, user_id: int, box_id: int) -> Dict[str, Any]:
    """
    Open a loot box from inventory using weighted random selection.
    Returns the reward details.
    """
    inv_item = (
        db.query(Inventory)
        .filter(Inventory.id == box_id, Inventory.user_id == user_id)
        .first()
    )
    if not inv_item:
        raise ValueError("Loot box not found in inventory.")

    if inv_item.category != "loot_box":
        raise ValueError("Item is not a loot box.")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found.")

    box_type = inv_item.effect.get("value", "common")
    pool = _LOOT_POOLS.get(box_type, _LOOT_POOLS["common"])

    # Weighted random selection
    rewards = pool["rewards"]
    weights = [r["weight"] for r in rewards]
    chosen = random.choices(rewards, weights=weights, k=1)[0]

    # Apply reward
    result = {"box_type": box_type, "reward": chosen}

    if chosen["type"] == "coins":
        user.coins += chosen["amount"]
        result["coins_added"] = chosen["amount"]
    elif chosen["type"] == "xp":
        user.total_xp += chosen["amount"]
        user.season_xp += chosen["amount"]
        result["xp_added"] = chosen["amount"]
    elif chosen["type"] == "item":
        # Add item to inventory
        new_inv = Inventory(
            user_id=user_id,
            item_id=chosen["item_id"],
            item_name=chosen["item_id"],
            category="bonus",
            effect={"type": "bonus", "value": chosen["item_id"]},
            rarity="bonus",
            quantity=1,
            purchased_at=datetime.utcnow(),
        )
        db.add(new_inv)
        result["item_added"] = chosen["item_id"]
    elif chosen["type"] == "badge":
        badges = user.badges or []
        if chosen["badge"] not in badges:
            badges.append(chosen["badge"])
            user.badges = badges
        result["badge_added"] = chosen["badge"]

    # Remove the loot box
    inv_item.quantity = max(0, inv_item.quantity - 1)
    if inv_item.quantity <= 0:
        db.delete(inv_item)

    db.commit()
    logger.info(f"User {user_id} opened {box_type} loot box, got: {chosen['type']}")
    return result


# Lucky wheel configuration
_WHEEL_SEGMENTS = [
    {"type": "coins", "label": "Coins", "min_amount": 50, "max_amount": 200, "weight": 40},
    {"type": "xp", "label": "XP", "min_amount": 50, "max_amount": 150, "weight": 25},
    {"type": "nothing", "label": "Nothing", "weight": 15},
    {"type": "boost", "label": "XP Boost", "duration": 1800, "multiplier": 2, "weight": 10},
    {"type": "chest", "label": "Loot Chest", "weight": 7},
    {"type": "badge", "label": "Badge", "badge": "wheel_fortune", "weight": 3},
]


def spin_lucky_wheel(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Spin the lucky wheel. Once per day (checked via Redis).
    Weights: 40% coins, 25% XP, 15% nothing, 10% boost, 7% chest, 3% badge.
    Returns the spin result.
    """
    # Check daily limit via Redis
    redis_client = _get_redis_client()
    if redis_client:
        today_key = f"chatquest:wheel:{user_id}:{date.today().isoformat()}"
        if redis_client.exists(today_key):
            raise ValueError("You already spun the wheel today. Come back tomorrow!")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found.")

    # Weighted random
    weights = [s["weight"] for s in _WHEEL_SEGMENTS]
    chosen = random.choices(_WHEEL_SEGMENTS, weights=weights, k=1)[0]

    result = {"type": chosen["type"], "label": chosen["label"]}

    if chosen["type"] == "coins":
        amount = random.randint(chosen["min_amount"], chosen["max_amount"])
        user.coins += amount
        result["amount"] = amount
    elif chosen["type"] == "xp":
        amount = random.randint(chosen["min_amount"], chosen["max_amount"])
        user.total_xp += amount
        user.season_xp += amount
        result["amount"] = amount
    elif chosen["type"] == "boost":
        user.xp_boost_active = True
        user.xp_boost_multiplier = chosen.get("multiplier", 2)
        user.xp_boost_expires = datetime.utcnow().timestamp() + chosen.get("duration", 1800)
        result["multiplier"] = chosen.get("multiplier", 2)
        result["duration"] = chosen.get("duration", 1800)
    elif chosen["type"] == "chest":
        # Give a common loot box
        inv_item = Inventory(
            user_id=user_id,
            item_id="loot_box_common",
            item_name="Common Loot Box",
            category="loot_box",
            effect={"type": "loot_box", "value": "common"},
            rarity="common",
            quantity=1,
            purchased_at=datetime.utcnow(),
        )
        db.add(inv_item)
    elif chosen["type"] == "badge":
        badges = user.badges or []
        badge = chosen.get("badge", "wheel_fortune")
        if badge not in badges:
            badges.append(badge)
            user.badges = badges
        result["badge"] = badge
    # "nothing" returns just type and label

    # Mark daily spin in Redis
    if redis_client:
        today_key = f"chatquest:wheel:{user_id}:{date.today().isoformat()}"
        redis_client.setex(today_key, 86400, "1")

    db.commit()
    logger.info(f"User {user_id} spun wheel, got: {chosen['type']}")
    return result


def _get_redis_client():
    """Get Redis client. Returns None if not available."""
    try:
        import redis
        from bot.core.config import settings
        client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
        )
        client.ping()
        return client
    except Exception:
        return None


def get_or_create_user(
    db: Session, user_id: int, default_data: Optional[Dict[str, Any]] = None
) -> User:
    """
    Get or create a user. Helper for service modules.
    Returns the User object.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        return user

    defaults = default_data or {}
    user = User(
        user_id=user_id,
        username=defaults.get("username"),
        chat_id=defaults.get("chat_id"),
        coins=defaults.get("coins", 0),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"Created new user {user_id}")
    return user
