from __future__ import annotations

from datetime import datetime, timedelta, timezone, date

from bot.models import User


def _today() -> date:
    return datetime.now(timezone.utc).date()


async def update_streak(user_id: int) -> int:
    """Update the user's activity streak.

    - If last active was yesterday  → increment streak
    - If last active was today     → keep same streak
    - Otherwise (gap >= 2 days)    → reset to 1
    """
    try:
        user = await User.find_one(User.telegram_id == user_id)
        if not user:
            return 0
    except Exception:
        return 0

    now = datetime.now(timezone.utc)
    today = now.date()
    last_active = user.last_active

    if last_active is None:
        user.streak = 1
    else:
        last_date = last_active.date() if isinstance(last_active, datetime) else last_active
        if last_date == today:
            pass  # already active today, keep streak
        elif last_date == today - timedelta(days=1):
            user.streak = (user.streak or 0) + 1
        else:
            user.streak = 1

    user.last_active = now
    await user.save()
    return user.streak or 0


def get_streak_reward(streak: int) -> dict:
    """Return the reward for a given *streak* value.

    Milestones:
      1   → 10 xp
      7   → 50 xp + 100 coins
      30  → 200 xp + 500 coins + title
      100 → 1000 xp + 2000 coins + badge
    Otherwise → streak * 5 xp
    """
    if streak >= 100:
        return {
            "xp": 1000,
            "coins": 2000,
            "bonus": "badge",
            "description": "🌟 Legendary streak! 1000 XP, 2000 coins & Badge",
        }
    if streak >= 30:
        return {
            "xp": 200,
            "coins": 500,
            "bonus": "title",
            "description": "👑 Epic streak! 200 XP, 500 coins & Title",
        }
    if streak >= 7:
        return {
            "xp": 50,
            "coins": 100,
            "bonus": None,
            "description": "🔥🔥 Weekly streak! 50 XP & 100 coins",
        }
    if streak >= 1:
        return {
            "xp": streak * 5,
            "coins": 0,
            "bonus": None,
            "description": f"🔥 Daily streak! {streak * 5} XP",
        }
    return {"xp": 0, "coins": 0, "bonus": None, "description": ""}


async def freeze_streak(user_id: int) -> bool:
    """Use a streak-freeze inventory item to preserve the user's streak.

    Returns True if the freeze was applied, False otherwise.
    """
    try:
        user = await User.find_one(User.telegram_id == user_id)
        if not user:
            return False
        powers = user.temporary_powers or []
        # Find a streak_freeze power in the list
        for i, p in enumerate(powers):
            if isinstance(p, dict) and p.get("type") == "streak_freeze" and p.get("count", 0) > 0:
                p["count"] -= 1
                if p["count"] <= 0:
                    powers.pop(i)
                user.temporary_powers = powers
                await user.save()
                return True
        return False
    except Exception:
        return False


def format_streak(streak: int) -> str:
    """Return a visual indicator for the streak.

    1-6   → 🔥
    7-29  → 🔥🔥
    30-99 → 👑
    100+  → 🌟
    """
    if streak >= 100:
        return "🌟"
    if streak >= 30:
        return "👑"
    if streak >= 7:
        return "🔥🔥"
    if streak >= 1:
        return "🔥"
    return ""
