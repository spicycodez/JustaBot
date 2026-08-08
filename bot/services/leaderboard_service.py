import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from bot.models.user import User
from bot.models.guild import Guild

logger = logging.getLogger(__name__)

# Redis key prefix
_REDIS_PREFIX = "chatquest:leaderboard"
_CACHE_TTL = 300  # 5 minutes

CATEGORY_COLUMNS = {
    "xp": User.season_xp,
    "coins": User.coins,
    "streak": User.streak,
    "reputation": User.reputation,
    "invites": User.total_referrals,
}


def _get_redis_key(chat_id: int, category: str) -> str:
    return f"{_REDIS_PREFIX}:{chat_id}:{category}"


def _get_redis_client():
    """Get Redis client. Returns None if Redis is not configured."""
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


def get_xp_leaderboard(
    db: Session, chat_id: int, limit: int = 10
) -> List[Dict[str, Any]]:
    """Get top users by season XP for a chat."""
    return _get_user_leaderboard(db, chat_id, "xp", limit)


def get_coins_leaderboard(
    db: Session, chat_id: int, limit: int = 10
) -> List[Dict[str, Any]]:
    """Get top users by coins for a chat."""
    return _get_user_leaderboard(db, chat_id, "coins", limit)


def get_streak_leaderboard(
    db: Session, chat_id: int, limit: int = 10
) -> List[Dict[str, Any]]:
    """Get top users by streak for a chat."""
    return _get_user_leaderboard(db, chat_id, "streak", limit)


def get_helpers_leaderboard(
    db: Session, chat_id: int, limit: int = 10
) -> List[Dict[str, Any]]:
    """Get top users by reputation for a chat."""
    return _get_user_leaderboard(db, chat_id, "reputation", limit)


def get_invites_leaderboard(
    db: Session, chat_id: int, limit: int = 10
) -> List[Dict[str, Any]]:
    """Get top users by referrals for a chat."""
    return _get_user_leaderboard(db, chat_id, "invites", limit)


def _get_user_leaderboard(
    db: Session, chat_id: int, category: str, limit: int
) -> List[Dict[str, Any]]:
    """Internal: get user leaderboard by category column."""
    column = CATEGORY_COLUMNS.get(category)
    if not column:
        return []

    users = (
        db.query(User)
        .filter(User.chat_id == chat_id)
        .order_by(column.desc())
        .limit(limit)
        .all()
    )

    result = []
    for rank, user in enumerate(users, 1):
        result.append({
            "rank": rank,
            "user_id": user.user_id,
            "username": user.username,
            "level": user.level,
            "value": getattr(user, column.key),
            "title": user.title,
            "guild_tag": None,  # Could join guild for this
        })
    return result


def get_guild_leaderboard(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    """Get top guilds by XP globally."""
    guilds = (
        db.query(Guild)
        .order_by(Guild.total_xp.desc())
        .limit(limit)
        .all()
    )

    result = []
    for rank, guild in enumerate(guilds, 1):
        result.append({
            "rank": rank,
            "id": guild.id,
            "name": guild.name,
            "tag": guild.tag,
            "emblem": guild.emblem,
            "level": guild.level,
            "total_xp": guild.total_xp,
            "member_count": guild.member_count,
            "owner_id": guild.owner_id,
        })
    return result


def update_leaderboard_cache(db: Session, chat_id: int) -> None:
    """Cache all leaderboard categories for a chat in Redis with 5min TTL."""
    redis_client = _get_redis_client()
    if not redis_client:
        return

    categories = ["xp", "coins", "streak", "reputation", "invites"]
    category_map = {
        "xp": get_xp_leaderboard,
        "coins": get_coins_leaderboard,
        "streak": get_streak_leaderboard,
        "reputation": get_helpers_leaderboard,
        "invites": get_invites_leaderboard,
    }

    for cat in categories:
        key = _get_redis_key(chat_id, cat)
        data = category_map[cat](db, chat_id, limit=50)
        try:
            redis_client.setex(key, _CACHE_TTL, json.dumps(data))
        except Exception as e:
            logger.warning(f"Failed to cache leaderboard {cat}: {e}")

    logger.info(f"Updated leaderboard cache for chat {chat_id}")


def get_cached_leaderboard(
    db: Session, chat_id: int, category: str
) -> List[Dict[str, Any]]:
    """Get leaderboard from Redis cache first, fall back to DB."""
    redis_client = _get_redis_client()
    if redis_client:
        key = _get_redis_key(chat_id, category)
        try:
            cached = redis_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    # Fallback to DB
    category_map = {
        "xp": get_xp_leaderboard,
        "coins": get_coins_leaderboard,
        "streak": get_streak_leaderboard,
        "reputation": get_helpers_leaderboard,
        "invites": get_invites_leaderboard,
        "guild": lambda db, cid, lim: get_guild_leaderboard(db, lim),
    }
    getter = category_map.get(category)
    if getter:
        return getter(db, chat_id, 10)
    return []


def get_user_rank(
    db: Session, user_id: int, chat_id: int, category: str
) -> Optional[Dict[str, Any]]:
    """Get a user's position in a leaderboard category."""
    column = CATEGORY_COLUMNS.get(category)
    if not column:
        return None

    # Get all users sorted by category
    all_users = (
        db.query(User)
        .filter(User.chat_id == chat_id)
        .order_by(column.desc())
        .all()
    )

    for rank, user in enumerate(all_users, 1):
        if user.user_id == user_id:
            return {
                "rank": rank,
                "user_id": user.user_id,
                "username": user.username,
                "value": getattr(user, column.key),
                "total_users": len(all_users),
            }

    return None
