from __future__ import annotations

from bot.models import User


def xp_required(level: int) -> int:
    """Return XP required to reach *level* from the previous one.

    Formula: 100 * level ** 1.5
    """
    return int(100 * (level ** 1.5))


def get_level_from_xp(xp: int) -> int:
    """Iterate levels until cumulative XP requirement exceeds *xp*.

    Returns the highest level whose total XP requirement does not exceed *xp*.
    """
    if xp < 0:
        return 1
    level = 1
    total = 0
    while True:
        needed = xp_required(level + 1)
        if total + needed > xp:
            return level
        total += needed
        level += 1


async def check_level_up(user_id: int, current_xp: int) -> tuple[bool, int | None]:
    """Determine if the user has leveled up based on *current_xp*.

    Returns (leveled_up: bool, new_level: int | None).
    """
    try:
        user = await User.find_one(User.telegram_id == user_id)
        if not user:
            return (False, None)
        new_level = get_level_from_xp(current_xp)
        leveled = new_level > user.level
        return (leveled, new_level if leveled else None)
    except Exception:
        return (False, None)


def get_rank_title(level: int) -> str:
    """Return the rank title for a given *level*.

    1-4   Newcomer
    5-9   Villager
    10-14 Warrior
    15-19 Knight
    20-24 Champion
    25-29 Hero
    30-39 Legend
    40+   Mythic
    """
    if level >= 40:
        return "Mythic"
    if level >= 30:
        return "Legend"
    if level >= 25:
        return "Hero"
    if level >= 20:
        return "Champion"
    if level >= 15:
        return "Knight"
    if level >= 10:
        return "Warrior"
    if level >= 5:
        return "Villager"
    return "Newcomer"


async def update_user_level(user: User) -> dict:
    """Recalculate and persist the user's level based on their current XP.

    Returns a dict with level information.
    """
    old_level = user.level
    new_level = get_level_from_xp(user.xp)
    new_rank = get_rank_title(new_level)

    user.level = new_level
    user.rank = new_rank
    await user.save()

    return {
        "old_level": old_level,
        "new_level": new_level,
        "rank": new_rank,
        "leveled_up": new_level > old_level,
    }
