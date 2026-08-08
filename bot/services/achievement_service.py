import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from bot.models.user import User

logger = logging.getLogger(__name__)

_ACHIEVEMENTS_DATA: Optional[List[Dict[str, Any]]] = None


def _load_achievements() -> List[Dict[str, Any]]:
    """Load achievements from data/achievements.json."""
    global _ACHIEVEMENTS_DATA
    if _ACHIEVEMENTS_DATA is None:
        import os
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "achievements.json",
        )
        with open(data_path, "r", encoding="utf-8") as f:
            _ACHIEVEMENTS_DATA = json.load(f)
    return _ACHIEVEMENTS_DATA


def _get_user_stat(user: User, stat_name: str) -> Any:
    """Get a stat value from a user object."""
    stat_map = {
        "total_messages": user.total_messages,
        "reputation": user.reputation,
        "streak": user.streak,
        "level": user.level,
        "coins": user.coins,
        "events_participated": user.events_participated,
        "guild_battles_won": user.guild_battles_won,
        "total_referrals": user.total_referrals,
        "night_messages": user.night_messages,
        "voice_minutes": user.voice_minutes,
        "guild_leader": user.guild_id is not None,
        "secret_found": user.secret_found,
    }
    return stat_map.get(stat_name, 0)


def _check_condition(user: User, condition: Dict[str, Any]) -> bool:
    """Check if a user meets a single achievement condition."""
    stat_value = _get_user_stat(user, condition["stat"])
    operator = condition["operator"]
    target = condition["value"]

    if operator == ">=":
        return stat_value >= target
    elif operator == "==":
        return stat_value == target
    elif operator == "<=":
        return stat_value <= target
    elif operator == ">":
        return stat_value > target
    elif operator == "<":
        return stat_value < target
    elif operator == "!=":
        return stat_value != target
    return False


def check_achievements(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """
    Compare user stats to all achievements and return newly earned ones.
    Automatically awards XP, coins, title, and badge.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return []

    all_achievements = _load_achievements()
    earned_ids = user.achievements or []
    newly_earned = []

    for ach in all_achievements:
        ach_id = ach["achievement_id"]
        if ach_id in earned_ids:
            continue

        if _check_condition(user, ach["condition"]):
            # Award it
            award_achievement(db, user_id, ach_id)
            newly_earned.append(ach)

    return newly_earned


def award_achievement(
    db: Session, user_id: int, achievement_id: str
) -> Dict[str, Any]:
    """
    Award an achievement to a user.
    Adds to user.achievements and awards XP/coins/title/badge.
    Returns achievement details.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found.")

    # Load achievement definition
    all_achievements = _load_achievements()
    ach_def = None
    for a in all_achievements:
        if a["achievement_id"] == achievement_id:
            ach_def = a
            break

    if not ach_def:
        raise ValueError(f"Achievement '{achievement_id}' not found.")

    # Check if already earned
    earned_ids = user.achievements or []
    if achievement_id in earned_ids:
        raise ValueError(f"User already has achievement '{achievement_id}'.")

    # Add to user's achievements
    earned_ids.append(achievement_id)
    user.achievements = earned_ids

    # Award rewards
    reward_xp = ach_def.get("reward_xp", 0)
    reward_coins = ach_def.get("reward_coins", 0)
    reward_title = ach_def.get("reward_title")
    reward_badge = ach_def.get("reward_badge")

    if reward_xp:
        user.total_xp += reward_xp
        user.season_xp += reward_xp
    if reward_coins:
        user.coins += reward_coins
    if reward_title:
        user.title = reward_title
    if reward_badge:
        badges = user.badges or []
        if reward_badge not in badges:
            badges.append(reward_badge)
            user.badges = badges

    db.commit()

    result = {
        "achievement_id": achievement_id,
        "title": ach_def["title"],
        "description": ach_def["description"],
        "icon": ach_def["icon"],
        "category": ach_def["category"],
        "reward_xp": reward_xp,
        "reward_coins": reward_coins,
        "reward_title": reward_title,
        "reward_badge": reward_badge,
        "earned_at": datetime.utcnow().isoformat(),
    }

    logger.info(f"User {user_id} earned achievement: {ach_def['title']}")
    return result


def get_user_achievements(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Get all achievements earned by a user with full details.
    Returns {"earned": [...], "count": int}.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return {"earned": [], "count": 0}

    earned_ids = user.achievements or []
    all_achievements = _load_achievements()

    earned = []
    for ach_id in earned_ids:
        for ach_def in all_achievements:
            if ach_def["achievement_id"] == ach_id:
                earned.append({
                    "achievement_id": ach_def["achievement_id"],
                    "title": ach_def["title"],
                    "description": ach_def["description"],
                    "icon": ach_def["icon"],
                    "category": ach_def["category"],
                })
                break

    return {"earned": earned, "count": len(earned)}


def get_all_achievements() -> List[Dict[str, Any]]:
    """
    Get all achievement definitions.
    Returns a list of all achievement dictionaries.
    """
    return _load_achievements()


def get_achievement_progress(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """
    For each unearned achievement, show progress percentage.
    Returns a list of progress dictionaries.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return []

    earned_ids = user.achievements or []
    all_achievements = _load_achievements()

    progress_list = []
    for ach_def in all_achievements:
        ach_id = ach_def["achievement_id"]
        if ach_id in earned_ids:
            continue

        condition = ach_def["condition"]
        stat_value = _get_user_stat(user, condition["stat"])
        target = condition["value"]

        # Calculate percentage
        if target == 0:
            percent = 100 if stat_value == target else 0
        elif isinstance(target, bool):
            percent = 100 if stat_value == target else 0
        else:
            percent = min(100, round((stat_value / target) * 100, 1))

        progress_list.append({
            "achievement_id": ach_id,
            "title": ach_def["title"],
            "description": ach_def["description"],
            "icon": ach_def["icon"],
            "category": ach_def["category"],
            "current": stat_value,
            "target": target,
            "progress_percent": percent,
        })

    return progress_list
