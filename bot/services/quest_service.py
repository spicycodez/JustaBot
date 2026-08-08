import json
import random
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from bot.models.user_quest import UserQuest
from bot.models.user import User

logger = logging.getLogger(__name__)

# Load quest definitions from data file
_QUESTS_DATA: Optional[List[Dict[str, Any]]] = None


def _load_quests() -> List[Dict[str, Any]]:
    """Load quests from data/quests.json."""
    global _QUESTS_DATA
    if _QUESTS_DATA is None:
        import os
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "quests.json",
        )
        with open(data_path, "r", encoding="utf-8") as f:
            _QUESTS_DATA = json.load(f)
    return _QUESTS_DATA


def _pick_quests(quest_type: str, difficulty: str, count: int) -> List[Dict[str, Any]]:
    """Pick random quests matching type and difficulty."""
    all_quests = _load_quests()
    pool = [
        q for q in all_quests
        if q["quest_type"] == quest_type and q["difficulty"] == difficulty
    ]
    if len(pool) < count:
        # Not enough quests of exact match, fill from same type
        pool = [q for q in all_quests if q["quest_type"] == quest_type]
    return random.sample(pool, min(count, len(pool)))


def generate_daily_quests(db: Session, user_id: int) -> List[UserQuest]:
    """
    Generate daily quests for a user: 3 easy + 2 medium + 1 hard.
    Removes any existing incomplete daily quests first.
    Returns list of created UserQuest objects.
    """
    # Remove existing incomplete daily quests
    existing = (
        db.query(UserQuest)
        .filter(
            UserQuest.user_id == user_id,
            UserQuest.quest_type == "daily",
            UserQuest.completed == False,
        )
        .all()
    )
    for eq in existing:
        db.delete(eq)
    db.flush()

    # Pick new quests
    easy = _pick_quests("daily", "easy", 3)
    medium = _pick_quests("daily", "medium", 2)
    hard = _pick_quests("daily", "hard", 1)
    selected = easy + medium + hard

    today = date.today()
    created_quests = []
    for quest_def in selected:
        user_quest = UserQuest(
            user_id=user_id,
            quest_id=quest_def["quest_id"],
            quest_type="daily",
            title=quest_def["title"],
            description=quest_def["description"],
            target=quest_def["target"],
            target_type=quest_def["target_type"],
            progress=0,
            reward_xp=quest_def["reward_xp"],
            reward_coins=quest_def["reward_coins"],
            difficulty=quest_def["difficulty"],
            completed=False,
            claimed=False,
            created_at=today,
        )
        db.add(user_quest)
        created_quests.append(user_quest)

    db.commit()
    for cq in created_quests:
        db.refresh(cq)

    logger.info(f"Generated {len(created_quests)} daily quests for user {user_id}")
    return created_quests


def generate_weekly_quests(db: Session, user_id: int) -> List[UserQuest]:
    """
    Generate weekly quests for a user: 5 random weekly quests.
    Removes any existing incomplete weekly quests first.
    Returns list of created UserQuest objects.
    """
    # Remove existing incomplete weekly quests
    existing = (
        db.query(UserQuest)
        .filter(
            UserQuest.user_id == user_id,
            UserQuest.quest_type == "weekly",
            UserQuest.completed == False,
        )
        .all()
    )
    for eq in existing:
        db.delete(eq)
    db.flush()

    all_weekly = _pick_quests("weekly", "easy", 100)  # get all weekly quests
    selected = random.sample(all_weekly, min(5, len(all_weekly)))

    today = date.today()
    created_quests = []
    for quest_def in selected:
        user_quest = UserQuest(
            user_id=user_id,
            quest_id=quest_def["quest_id"],
            quest_type="weekly",
            title=quest_def["title"],
            description=quest_def["description"],
            target=quest_def["target"],
            target_type=quest_def["target_type"],
            progress=0,
            reward_xp=quest_def["reward_xp"],
            reward_coins=quest_def["reward_coins"],
            difficulty=quest_def["difficulty"],
            completed=False,
            claimed=False,
            created_at=today,
        )
        db.add(user_quest)
        created_quests.append(user_quest)

    db.commit()
    for cq in created_quests:
        db.refresh(cq)

    logger.info(f"Generated {len(created_quests)} weekly quests for user {user_id}")
    return created_quests


def update_quest_progress(
    db: Session, user_id: int, quest_type: str, amount: int = 1
) -> List[Dict[str, Any]]:
    """
    Update quest progress for a user matching the target_type.
    Increment progress and return list of newly completed quests.
    """
    active_quests = (
        db.query(UserQuest)
        .filter(
            UserQuest.user_id == user_id,
            UserQuest.target_type == quest_type,
            UserQuest.completed == False,
        )
        .all()
    )

    newly_completed = []
    for quest in active_quests:
        quest.progress = min(quest.progress + amount, quest.target)
        if quest.progress >= quest.target and not quest.completed:
            quest.completed = True
            quest.completed_at = datetime.utcnow()
            newly_completed.append({
                "quest_id": quest.quest_id,
                "title": quest.title,
                "reward_xp": quest.reward_xp,
                "reward_coins": quest.reward_coins,
            })
            logger.info(
                f"User {user_id} completed quest '{quest.title}'"
            )

    db.commit()
    return newly_completed


def complete_quest(db: Session, user_id: int, quest_id: str) -> UserQuest:
    """
    Mark a quest as completed and award rewards.
    Returns the updated UserQuest.
    """
    quest = (
        db.query(UserQuest)
        .filter(
            UserQuest.user_id == user_id,
            UserQuest.quest_id == quest_id,
            UserQuest.completed == False,
        )
        .first()
    )
    if not quest:
        raise ValueError(f"Active quest '{quest_id}' not found for user {user_id}.")

    quest.completed = True
    quest.completed_at = datetime.utcnow()

    # Award rewards
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        user.total_xp += quest.reward_xp
        user.season_xp += quest.reward_xp
        user.coins += quest.reward_coins

    db.commit()
    db.refresh(quest)
    logger.info(
        f"User {user_id} completed quest '{quest.title}': +{quest.reward_xp} XP, +{quest.reward_coins} coins"
    )
    return quest


def claim_quest_reward(db: Session, user_id: int, quest_id: str) -> Dict[str, Any]:
    """
    Claim reward for a completed but unclaimed quest.
    Returns a dict with reward details.
    """
    quest = (
        db.query(UserQuest)
        .filter(
            UserQuest.user_id == user_id,
            UserQuest.quest_id == quest_id,
            UserQuest.completed == True,
            UserQuest.claimed == False,
        )
        .first()
    )
    if not quest:
        raise ValueError(
            f"No completed and unclaimed quest '{quest_id}' found for user {user_id}."
        )

    quest.claimed = True
    quest.claimed_at = datetime.utcnow()

    # Award rewards
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        user.total_xp += quest.reward_xp
        user.season_xp += quest.reward_xp
        user.coins += quest.reward_coins

    db.commit()
    db.refresh(quest)

    logger.info(
        f"User {user_id} claimed reward for quest '{quest.title}': +{quest.reward_xp} XP, +{quest.reward_coins} coins"
    )
    return {
        "quest_id": quest.quest_id,
        "title": quest.title,
        "reward_xp": quest.reward_xp,
        "reward_coins": quest.reward_coins,
        "claimed_at": quest.claimed_at.isoformat() if quest.claimed_at else None,
    }


def get_user_quests(db: Session, user_id: int) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get all quests for a user organized by status.
    Returns {"daily": [], "weekly": [], "completed": []}
    """
    quests = (
        db.query(UserQuest)
        .filter(UserQuest.user_id == user_id)
        .all()
    )

    result = {"daily": [], "weekly": [], "completed": []}
    for q in quests:
        quest_data = {
            "quest_id": q.quest_id,
            "title": q.title,
            "description": q.description,
            "quest_type": q.quest_type,
            "difficulty": q.difficulty,
            "target": q.target,
            "target_type": q.target_type,
            "progress": q.progress,
            "reward_xp": q.reward_xp,
            "reward_coins": q.reward_coins,
            "completed": q.completed,
            "claimed": q.claimed,
        }

        if q.completed:
            result["completed"].append(quest_data)
        elif q.quest_type == "daily":
            result["daily"].append(quest_data)
        elif q.quest_type == "weekly":
            result["weekly"].append(quest_data)

    return result


def reset_all_daily_quests(db: Session) -> int:
    """
    Reset all daily quests. Called by scheduler at midnight.
    Deletes all daily quests (completed or not).
    Returns count of deleted quests.
    """
    count = (
        db.query(UserQuest)
        .filter(UserQuest.quest_type == "daily")
        .delete()
    )
    db.commit()
    logger.info(f"Reset all daily quests. Deleted {count} quests.")
    return count


def reset_all_weekly_quests(db: Session) -> int:
    """
    Reset all weekly quests. Called by scheduler on Monday.
    Deletes all weekly quests (completed or not).
    Returns count of deleted quests.
    """
    count = (
        db.query(UserQuest)
        .filter(UserQuest.quest_type == "weekly")
        .delete()
    )
    db.commit()
    logger.info(f"Reset all weekly quests. Deleted {count} quests.")
    return count
