from __future__ import annotations

from datetime import datetime, date, timezone

from bot.models import User
from bot.services.streak_service import update_streak


async def award_coins(user_id: int, amount: int, reason: str) -> int:
    """Add *amount* coins to the user. Returns new coin balance."""
    try:
        user = await User.find_one(User.telegram_id == user_id)
        if not user:
            return 0
        user.coins = (user.coins or 0) + amount
        await user.save()
        return user.coins
    except Exception:
        return 0


async def deduct_coins(user_id: int, amount: int) -> bool:
    """Deduct *amount* coins from the user. Returns True on success."""
    try:
        user = await User.find_one(User.telegram_id == user_id)
        if not user:
            return False
        if (user.coins or 0) < amount:
            return False
        user.coins = user.coins - amount
        await user.save()
        return True
    except Exception:
        return False


def get_daily_reward(day: int) -> dict:
    """Return the daily-reward configuration for the given *day* of streak.

    Special days:
      1  → 100 coins
      2  → 150 coins
      3  → XP boost (temporary power)
      4  → 200 coins
      5  → 250 coins
      6  → Lucky ticket
      7  → Epic chest
      14 → 500 coins
      21 → Rare lootbox
      30 → Legend chest
    Other → day × 50 coins
    """
    specials: dict[int, dict] = {
        1:  {"type": "coins",         "amount": 100,         "label": "💰 100 Coins"},
        2:  {"type": "coins",         "amount": 150,         "label": "💰 150 Coins"},
        3:  {"type": "xp_boost",      "amount": 0,           "label": "⚡ XP Boost Power"},
        4:  {"type": "coins",         "amount": 200,         "label": "💰 200 Coins"},
        5:  {"type": "coins",         "amount": 250,         "label": "💰 250 Coins"},
        6:  {"type": "lucky_ticket",   "amount": 1,           "label": "🎫 Lucky Ticket"},
        7:  {"type": "epic_chest",     "amount": 1,           "label": "🎁 Epic Chest"},
        14: {"type": "coins",         "amount": 500,         "label": "💰 500 Coins"},
        21: {"type": "rare_lootbox",   "amount": 1,           "label": "🎁 Rare Lootbox"},
        30: {"type": "legend_chest",  "amount": 1,           "label": "🏆 Legend Chest"},
    }

    if day in specials:
        return specials[day]
    return {"type": "coins", "amount": day * 50, "label": f"💰 {day * 50} Coins"}


async def claim_daily_reward(user_id: int) -> dict:
    """Process a daily-reward claim.

    Handles streak logic:
      - Claimed yesterday → streak continues
      - Claimed today    → already claimed
      - Older            → streak resets to 1

    Returns dict with: reward, streak, new_coins, message.
    """
    try:
        user = await User.find_one(User.telegram_id == user_id)
        if not user:
            return {"reward": None, "streak": 0, "new_coins": 0, "message": "User not found."}
    except Exception:
        return {"reward": None, "streak": 0, "new_coins": 0, "message": "Failed to retrieve user."}

    today = datetime.now(timezone.utc).date()
    last_claim = user.last_daily_claim

    if last_claim is not None:
        last_date = last_claim if isinstance(last_claim, date) else last_claim.date()
        if last_date == today:
            return {
                "reward": None,
                "streak": user.streak or 0,
                "new_coins": user.coins or 0,
                "message": "You already claimed your daily reward today! Come back tomorrow.",
            }

    # Update streak via streak_service
    streak = await update_streak(user_id)
    day = streak

    reward = get_daily_reward(day)
    coins_gained = 0

    if reward["type"] == "coins":
        coins_gained = reward["amount"]
        user.coins = (user.coins or 0) + coins_gained
    elif reward["type"] == "xp_boost":
        powers = list(user.temporary_powers or [])
        # Look for existing xp_boost, else append
        found = False
        for p in powers:
            if isinstance(p, dict) and p.get("type") == "xp_boost":
                p["count"] = p.get("count", 0) + 1
                found = True
                break
        if not found:
            powers.append({"type": "xp_boost", "count": 1})
        user.temporary_powers = powers
    elif reward["type"] in ("lucky_ticket", "epic_chest", "rare_lootbox", "legend_chest"):
        powers = list(user.temporary_powers or [])
        # Look for existing item, else append
        found = False
        for p in powers:
            if isinstance(p, dict) and p.get("type") == "inventory":
                p.setdefault("items", []).append(reward["type"])
                found = True
                break
        if not found:
            powers.append({"type": "inventory", "items": [reward["type"]]})
        user.temporary_powers = powers

    user.last_daily_claim = today
    user.streak = streak
    await user.save()

    return {
        "reward": reward,
        "streak": streak,
        "new_coins": user.coins or 0,
        "coins_gained": coins_gained,
        "message": f"Day {day} reward: {reward['label']}",
    }
