from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from bot.cache import get_cache, set_cache
from bot.config import settings
from bot.models import User, UserQuest, Achievement
from bot.services.level_service import xp_required, check_level_up, get_level_from_xp, get_rank_title
from bot.services.streak_service import update_streak
from bot.services.anti_spam import check_spam as _check_spam, is_user_frozen


XP_COOLDOWN = settings.XP_COOLDOWN  # 20 seconds


async def _get_or_create_user(user_id: int, chat_id: int = 0) -> User | None:
    """Find user by telegram_id or create a minimal one."""
    try:
        user = await User.find_one(User.telegram_id == user_id)
        if user:
            return user
        # Create a new user – chat_id defaults to 0 if not available
        user = User(
            telegram_id=user_id,
            chat_id=chat_id or user_id,
            first_name="User",
        )
        await user.insert()
        return user
    except Exception:
        return None


async def _set_cooldown(user_id: int, chat_id: int) -> None:
    key = f"cooldown:{user_id}:{chat_id}"
    await set_cache(key, "1", expire=XP_COOLDOWN)


async def _check_cooldown(user_id: int, chat_id: int) -> bool:
    key = f"cooldown:{user_id}:{chat_id}"
    return (await get_cache(key)) is not None


async def _update_quest_progress(user_id: int, xp_gained: int) -> None:
    try:
        quests = await UserQuest.find(
            {
                "user_id": user_id,
                "quest_id": {"$in": ["daily_messages", "weekly_xp", "season_xp"]},
                "is_completed": False,
            }
        ).to_list()
        for quest in quests:
            quest.progress = (quest.progress or 0) + xp_gained
            if quest.progress >= (quest.target or 0):
                quest.is_completed = True
            await quest.save()
    except Exception:
        pass


async def _check_achievements(user_id: int, user: User) -> list[dict]:
    """Check and unlock matching achievements. Returns list of newly unlocked."""
    unlocked = []
    try:
        user_achievements = set(user.achievements or [])
        achievements = await Achievement.find().to_list()
        for ach in achievements:
            if ach.achievement_id in user_achievements:
                continue
            met = False
            cond = ach.condition_type
            val = ach.condition_value
            if cond == "total_messages" and (user.total_messages or 0) >= val:
                met = True
            elif cond == "total_replies" and (user.total_replies or 0) >= val:
                met = True
            elif cond == "streak" and (user.streak or 0) >= val:
                met = True
            elif cond == "level" and (user.level or 1) >= val:
                met = True
            elif cond == "reputation" and (user.reputation or 0) >= val:
                met = True
            elif cond == "total_xp" and (user.total_xp or 0) >= val:
                met = True

            if met:
                user_achievements.add(ach.achievement_id)
                # Award rewards
                user.xp = (user.xp or 0) + (ach.reward_xp or 0)
                user.total_xp = (user.total_xp or 0) + (ach.reward_xp or 0)
                user.coins = (user.coins or 0) + (ach.reward_coins or 0)
                unlocked.append({
                    "achievement_id": ach.achievement_id,
                    "reward_xp": ach.reward_xp,
                    "reward_coins": ach.reward_coins,
                })

        user.achievements = list(user_achievements)
        await user.save()
    except Exception:
        pass
    return unlocked


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def calculate_message_xp(message_text: str, is_reply: bool, has_file: bool) -> int:
    """Calculate base XP for a text message.

    < 10 chars → 0 XP
    10-40 chars → 2 XP
    40+ chars → 5 XP
    +8 XP for reply
    +10 XP for file attachment
    """
    length = len(message_text or "")
    if length < 10:
        base = 0
    elif length < 40:
        base = 2
    else:
        base = 5

    if is_reply:
        base += 8
    if has_file:
        base += 10

    return base


async def award_message_xp(
    user_id: int,
    chat_id: int,
    message_text: str,
    is_reply: bool,
    has_file: bool,
) -> dict:
    """Full message-XP pipeline.

    Returns {"xp_gained": int, "leveled_up": bool, "new_level": int|None, "coins_gained": int}
    """
    result = {"xp_gained": 0, "leveled_up": False, "new_level": None, "coins_gained": 0}

    try:
        # 1. Get / create user
        user = await _get_or_create_user(user_id, chat_id)
        if user is None:
            return result

        # 2. Check frozen
        if await is_user_frozen(user_id):
            return result

        # 3. Anti-spam check
        spam = await _check_spam(user_id, chat_id, message_text or "")
        if spam["is_spam"] and spam["freeze_duration"] > 0:
            user.xp_frozen_until = datetime.now(timezone.utc) + timedelta(seconds=spam["freeze_duration"])
            user.spam_count = spam["spam_count"]
            await user.save()
            return result
        if spam["is_spam"]:
            return result

        # 4. Cooldown check
        if await _check_cooldown(user_id, chat_id):
            return result

        # 5. Calculate XP
        xp = calculate_message_xp(message_text, is_reply, has_file)
        if xp <= 0:
            return result

        # 6. Award XP + random 1-3 coins
        coins = random.randint(1, 3)
        user.xp = (user.xp or 0) + xp
        user.total_xp = (user.total_xp or 0) + xp
        user.season_xp = (user.season_xp or 0) + xp
        user.coins = (user.coins or 0) + coins
        user.total_messages = (user.total_messages or 0) + 1
        if is_reply:
            user.total_replies = (user.total_replies or 0) + 1
        user.last_message_text = message_text
        user.last_message_time = datetime.now(timezone.utc)

        # 7. Check level up
        leveled_up, new_level = await check_level_up(user_id, user.xp)
        if leveled_up and new_level:
            user.level = new_level
            user.rank = get_rank_title(new_level)

        await user.save()

        # 8. Update streak
        await update_streak(user_id)

        # 9. Quest progress
        await _update_quest_progress(user_id, xp)

        # 10. Achievements
        await _check_achievements(user_id, user)

        # 11. Set cooldown
        await _set_cooldown(user_id, chat_id)

        result["xp_gained"] = xp
        result["leveled_up"] = leveled_up
        result["new_level"] = new_level
        result["coins_gained"] = coins

    except Exception:
        pass

    return result


async def award_reaction_xp(user_id: int, chat_id: int, reaction_type: str) -> int:
    """Award XP for reactions received.

    heart  → 6 XP
    pinned → 15 XP
    """
    mapping = {"heart": 6, "pinned": 15}
    xp = mapping.get(reaction_type, 0)
    if xp <= 0:
        return 0
    try:
        user = await _get_or_create_user(user_id, chat_id)
        if not user:
            return 0
        user.xp = (user.xp or 0) + xp
        user.total_xp = (user.total_xp or 0) + xp
        user.season_xp = (user.season_xp or 0) + xp
        await user.save()
    except Exception:
        return 0
    return xp


async def award_voice_xp(user_id: int, duration_minutes: int) -> int:
    """Award XP for voice messages. 20 base + 2 per 10 min."""
    xp = 20 + (duration_minutes // 10) * 2
    try:
        user = await _get_or_create_user(user_id)
        if not user:
            return 0
        user.xp = (user.xp or 0) + xp
        user.total_xp = (user.total_xp or 0) + xp
        user.season_xp = (user.season_xp or 0) + xp
        await user.save()
    except Exception:
        return 0
    return xp


async def award_event_xp(user_id: int, is_host: bool) -> int:
    """Participant → 20 XP, host → 40 XP."""
    xp = 40 if is_host else 20
    try:
        user = await _get_or_create_user(user_id)
        if not user:
            return 0
        user.xp = (user.xp or 0) + xp
        user.total_xp = (user.total_xp or 0) + xp
        user.season_xp = (user.season_xp or 0) + xp
        await user.save()
    except Exception:
        return 0
    return xp


async def award_invite_xp(user_id: int) -> int:
    """Invite reward → 50 XP."""
    xp = 50
    try:
        user = await _get_or_create_user(user_id)
        if not user:
            return 0
        user.xp = (user.xp or 0) + xp
        user.total_xp = (user.total_xp or 0) + xp
        user.season_xp = (user.season_xp or 0) + xp
        await user.save()
    except Exception:
        return 0
    return xp


async def award_referral_bonus(user_id: int, bonus_type: str) -> int:
    """Referral milestones.

    join   → 50 XP
    7_days → 150 XP
    level5 → 300 coins
    """
    try:
        user = await _get_or_create_user(user_id)
        if not user:
            return 0
        if bonus_type == "join":
            xp = 50
            user.xp = (user.xp or 0) + xp
            user.total_xp = (user.total_xp or 0) + xp
            await user.save()
            return xp
        elif bonus_type == "7_days":
            xp = 150
            user.xp = (user.xp or 0) + xp
            user.total_xp = (user.total_xp or 0) + xp
            await user.save()
            return xp
        elif bonus_type == "level5":
            user.coins = (user.coins or 0) + 300
            await user.save()
            return 0  # coins, not xp
        return 0
    except Exception:
        return 0


async def award_quest_xp(user_id: int, quest_id: str) -> int:
    """Quest completion reward → 100 XP base."""
    xp = 100
    try:
        user = await _get_or_create_user(user_id)
        if not user:
            return 0
        user.xp = (user.xp or 0) + xp
        user.total_xp = (user.total_xp or 0) + xp
        user.season_xp = (user.season_xp or 0) + xp
        await user.save()

        # Mark quest as claimed if it exists
        try:
            quest = await UserQuest.find_one(
                UserQuest.user_id == user_id,
                UserQuest.quest_id == quest_id,
            )
            if quest:
                quest.claimed = True
                await quest.save()
        except Exception:
            pass
    except Exception:
        return 0
    return xp


async def award_battle_xp(guild_id: str, user_id: int, is_winner: bool) -> int:
    """Battle results. Winner → 300 XP, loser → 50 XP."""
    xp = 300 if is_winner else 50
    try:
        user = await _get_or_create_user(user_id)
        if not user:
            return 0
        user.xp = (user.xp or 0) + xp
        user.total_xp = (user.total_xp or 0) + xp
        user.season_xp = (user.season_xp or 0) + xp
        await user.save()
    except Exception:
        return 0
    return xp
