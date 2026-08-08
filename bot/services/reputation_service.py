from __future__ import annotations

from bot.cache import increment_cache, set_cache, get_cache
from bot.config import settings
from bot.models import User


MAX_DAILY_THANKS = settings.MAX_DAILY_THANKS  # 5


async def give_thanks(from_user_id: int, to_user_id: int, chat_id: int) -> dict:
    """Give +1 reputation from one user to another.

    Rules:
      - Cannot thank yourself
      - Limited to MAX_DAILY_THANKS per user per day (tracked in Redis)
    """
    if from_user_id == to_user_id:
        return {
            "success": False,
            "reputation": 0,
            "remaining": 0,
            "message": "You can't thank yourself!",
        }

    # Daily limit key: thanks:{chat_id}:{from_user_id}
    key = f"thanks:{chat_id}:{from_user_id}"
    new_val = await increment_cache(key)
    remaining = MAX_DAILY_THANKS - new_val

    if remaining < 0:
        # Can't directly decrement via our helper; set to max
        await set_cache(key, str(MAX_DAILY_THANKS))
        return {
            "success": False,
            "reputation": 0,
            "remaining": 0,
            "message": f"You've already thanked {MAX_DAILY_THANKS} people today. Come back tomorrow!",
        }

    try:
        to_user = await User.find_one(User.telegram_id == to_user_id)
        if not to_user:
            return {
                "success": False,
                "reputation": 0,
                "remaining": remaining,
                "message": "User not found.",
            }
        to_user.reputation = (to_user.reputation or 0) + 1
        await to_user.save()
        return {
            "success": True,
            "reputation": to_user.reputation,
            "remaining": remaining,
            "message": f"Thanked! Their reputation is now {to_user.reputation}.",
        }
    except Exception as exc:
        return {
            "success": False,
            "reputation": 0,
            "remaining": remaining,
            "message": f"Error: {exc}",
        }


async def get_user_reputation(user_id: int) -> int:
    """Return the reputation score for a user."""
    try:
        user = await User.find_one(User.telegram_id == user_id)
        return user.reputation if user else 0
    except Exception:
        return 0


async def get_top_reputation(chat_id: int, limit: int = 10) -> list:
    """Return top users by reputation.

    Falls back to a global query if chat-scoped data is not available.
    """
    try:
        users = (
            await User.find({"reputation": {"$gt": 0}})
            .sort("-reputation")
            .limit(limit)
            .to_list()
        )
        return [
            {
                "telegram_id": u.telegram_id,
                "reputation": u.reputation or 0,
                "level": u.level or 1,
                "rank": u.rank or "Newcomer",
            }
            for u in users
        ]
    except Exception:
        return []
