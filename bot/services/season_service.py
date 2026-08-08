import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from bot.models.user import User
from bot.models.season import Season

logger = logging.getLogger(__name__)

SEASON_DURATION_DAYS = 30

# Season end rewards
SEASON_REWARDS = {
    "top_1": {
        "title": "Legend Crown",
        "badge": "season_legend",
        "xp": 5000,
        "role": "Season Champion",
    },
    "top_10": {
        "title": None,
        "badge": "season_epic",
        "xp": 2000,
        "role": "Season Elite",
    },
    "top_50": {
        "title": None,
        "badge": "season_special",
        "xp": 1000,
        "role": "Season Veteran",
    },
    "all": {
        "title": None,
        "badge": None,
        "xp": 200,
        "role": None,
    },
}


def get_current_season(db: Session) -> Season:
    """
    Get the current active season, or create a new one if none exists.
    Returns the Season object.
    """
    season = (
        db.query(Season)
        .filter(Season.status == "active")
        .order_by(Season.season_number.desc())
        .first()
    )

    if not season:
        season = create_new_season(db)

    return season


def create_new_season(db: Session) -> Season:
    """
    Create a new season. Ends any current season first.
    Returns the newly created Season object.
    """
    # End current season if exists
    current = (
        db.query(Season)
        .filter(Season.status == "active")
        .first()
    )
    if current:
        current.status = "completed"
        current.ended_at = datetime.utcnow()

    # Determine next season number
    last_season = (
        db.query(Season)
        .order_by(Season.season_number.desc())
        .first()
    )
    next_number = (last_season.season_number + 1) if last_season else 1

    season = Season(
        season_number=next_number,
        status="active",
        started_at=datetime.utcnow(),
        ends_at=datetime.utcnow() + timedelta(days=SEASON_DURATION_DAYS),
    )
    db.add(season)
    db.commit()
    db.refresh(season)

    logger.info(f"Season {next_number} created.")
    return season


def reset_season(db: Session) -> Dict[str, Any]:
    """
    Reset the season. Called by scheduler.
    Records top players, distributes rewards, creates new season.
    Returns a summary of rewards distributed.
    """
    current = get_current_season(db)
    if not current:
        return {"message": "No active season to reset."}

    # Get season leaderboard (top users by season_xp)
    top_users = (
        db.query(User)
        .order_by(User.season_xp.desc())
        .limit(50)
        .all()
    )

    rewards_distributed = []

    # Distribute rewards
    for rank, user in enumerate(top_users, 1):
        if rank == 1:
            reward_tier = "top_1"
        elif rank <= 10:
            reward_tier = "top_10"
        elif rank <= 50:
            reward_tier = "top_50"
        else:
            reward_tier = "all"

        reward = SEASON_REWARDS[reward_tier]

        # Award XP
        if reward["xp"]:
            user.total_xp += reward["xp"]

        # Award title
        if reward["title"]:
            user.title = reward["title"]

        # Award badge
        if reward["badge"]:
            badges = user.badges or []
            if reward["badge"] not in badges:
                badges.append(reward["badge"])
                user.badges = badges

        rewards_distributed.append({
            "user_id": user.user_id,
            "rank": rank,
            "season_xp": user.season_xp,
            "tier": reward_tier,
            "xp_rewarded": reward["xp"],
            "title": reward["title"],
            "badge": reward["badge"],
        })

    # Award 200 XP to ALL users who participated (season_xp > 0)
    all_participants = (
        db.query(User)
        .filter(User.season_xp > 0)
        .all()
    )
    participant_ids = {u.user_id for u in top_users}
    for user in all_participants:
        if user.user_id not in participant_ids:
            user.total_xp += SEASON_REWARDS["all"]["xp"]
            rewards_distributed.append({
                "user_id": user.user_id,
                "rank": None,
                "season_xp": user.season_xp,
                "tier": "all",
                "xp_rewarded": SEASON_REWARDS["all"]["xp"],
                "title": None,
                "badge": None,
            })

    # Reset all season XP
    db.query(User).update({User.season_xp: 0})

    # End current season
    current.status = "completed"
    current.ended_at = datetime.utcnow()
    current.total_participants = len(all_participants)

    # Create new season
    new_season = create_new_season(db)

    logger.info(
        f"Season {current.season_number} reset. {len(rewards_distributed)} rewards distributed. Season {new_season.season_number} started."
    )

    return {
        "completed_season": current.season_number,
        "new_season": new_season.season_number,
        "total_participants": len(all_participants),
        "rewards_distributed": rewards_distributed,
    }


def get_season_leaderboard(
    db: Session, season_number: Optional[int] = None, category: str = "xp"
) -> List[Dict[str, Any]]:
    """
    Get the leaderboard for a specific season or current season.
    Category: 'xp' (default).
    Returns a list of user dictionaries.
    """
    if season_number is not None:
        season = (
            db.query(Season)
            .filter(Season.season_number == season_number)
            .first()
        )
        if not season:
            return []

    # For current season, just use season_xp
    users = (
        db.query(User)
        .filter(User.season_xp > 0)
        .order_by(User.season_xp.desc())
        .limit(50)
        .all()
    )

    result = []
    for rank, user in enumerate(users, 1):
        result.append({
            "rank": rank,
            "user_id": user.user_id,
            "username": user.username,
            "level": user.level,
            "season_xp": user.season_xp,
            "guild_tag": None,
        })

    return result


def get_season_info(db: Session) -> Dict[str, Any]:
    """
    Get current season information.
    Returns season number, time remaining, and progress.
    """
    season = get_current_season(db)

    now = datetime.utcnow()
    if season.ends_at and season.started_at:
        total_duration = (season.ends_at - season.started_at).total_seconds()
        elapsed = (now - season.started_at).total_seconds()
        remaining = max(0, (season.ends_at - now).total_seconds())
        progress = min(100, round((elapsed / total_duration) * 100, 1))
    else:
        remaining = 0
        progress = 0

    # Format remaining time
    days = int(remaining // 86400)
    hours = int((remaining % 86400) // 3600)

    return {
        "season_number": season.season_number,
        "status": season.status,
        "started_at": season.started_at.isoformat() if season.started_at else None,
        "ends_at": season.ends_at.isoformat() if season.ends_at else None,
        "time_remaining_seconds": int(remaining),
        "time_remaining_display": f"{days}d {hours}h",
        "progress_percent": progress,
    }
