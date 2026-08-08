import logging
import math
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from bot.models.guild import Guild
from bot.models.user import User

logger = logging.getLogger(__name__)

# XP thresholds for guild levels
GUILD_LEVEL_XP = {
    1: 0,
    2: 500,
    3: 1500,
    4: 3500,
    5: 7000,
    6: 12000,
    7: 20000,
    8: 32000,
    9: 50000,
    10: 75000,
}


def _get_guild_level(total_xp: int) -> int:
    """Calculate guild level from total XP."""
    level = 1
    for lvl, threshold in sorted(GUILD_LEVEL_XP.items()):
        if total_xp >= threshold:
            level = lvl
        else:
            break
    return level


def _get_xp_for_next_level(level: int) -> Optional[int]:
    """Get XP needed for the next level."""
    return GUILD_LEVEL_XP.get(level + 1)


def _get_xp_for_current_level(level: int) -> int:
    """Get XP threshold for current level."""
    return GUILD_LEVEL_XP.get(level, 0)


def create_guild(db: Session, name: str, tag: str, owner_id: int, chat_id: int) -> Guild:
    """
    Create a new guild and add the owner as a member.
    Returns the created Guild object.
    """
    # Check if tag is already taken
    existing = db.query(Guild).filter(Guild.tag == tag.upper()).first()
    if existing:
        raise ValueError(f"Guild tag '{tag}' is already taken.")

    # Check if user is already in a guild
    owner = db.query(User).filter(User.user_id == owner_id).first()
    if owner and owner.guild_id:
        raise ValueError(f"User is already a member of a guild.")

    guild = Guild(
        name=name,
        tag=tag.upper(),
        owner_id=owner_id,
        chat_id=chat_id,
        total_xp=0,
        guild_coins=0,
        level=1,
        member_count=1,
        emblem=None,
    )
    db.add(guild)
    db.flush()  # Get the guild ID

    # Add owner as guild member
    if owner:
        owner.guild_id = guild.id
        owner.guild_name = guild.name
    else:
        # Create user if doesn't exist
        owner = User(
            user_id=owner_id,
            guild_id=guild.id,
            guild_name=guild.name,
        )
        db.add(owner)

    db.commit()
    db.refresh(guild)
    logger.info(f"Guild '{name}' [{tag}] created by user {owner_id}")
    return guild


def join_guild(db: Session, guild_name_or_tag: str, user_id: int) -> Guild:
    """
    Add a user to a guild by name or tag.
    Updates user.guild_id and user.guild_name.
    Returns the Guild object.
    """
    # Find guild by name or tag
    guild = (
        db.query(Guild)
        .filter(
            (Guild.name.ilike(guild_name_or_tag))
            | (Guild.tag == guild_name_or_tag.upper())
        )
        .first()
    )
    if not guild:
        raise ValueError(f"Guild '{guild_name_or_tag}' not found.")

    # Check user
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found.")
    if user.guild_id:
        raise ValueError("User is already in a guild. Leave first.")

    # Add to guild
    user.guild_id = guild.id
    user.guild_name = guild.name
    guild.member_count += 1

    db.commit()
    db.refresh(guild)
    logger.info(f"User {user_id} joined guild '{guild.name}'")
    return guild


def leave_guild(db: Session, user_id: int) -> bool:
    """
    Remove a user from their guild.
    If the user is the owner, transfer ownership to the most senior member
    or disband if they are the only member.
    Returns True if successful.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user or not user.guild_id:
        raise ValueError("User is not in a guild.")

    guild = db.query(Guild).filter(Guild.id == user.guild_id).first()
    if not guild:
        user.guild_id = None
        user.guild_name = None
        db.commit()
        return True

    if guild.owner_id == user_id:
        # Owner is leaving - find another member or disband
        other_members = (
            db.query(User)
            .filter(User.guild_id == guild.id, User.user_id != user_id)
            .order_by(User.total_xp.desc())
            .all()
        )

        if other_members:
            # Transfer ownership to the most senior member
            new_owner = other_members[0]
            guild.owner_id = new_owner.user_id
            logger.info(
                f"Guild '{guild.name}' ownership transferred from {user_id} to {new_owner.user_id}"
            )
        else:
            # Disband the guild
            db.delete(guild)
            logger.info(f"Guild '{guild.name}' disbanded (last member left)")
    else:
        guild.member_count = max(0, guild.member_count - 1)

    user.guild_id = None
    user.guild_name = None
    db.commit()
    logger.info(f"User {user_id} left guild '{guild.name}'")
    return True


def get_guild_info(db: Session, guild_id: int) -> Optional[Dict[str, Any]]:
    """
    Get full stats for a guild.
    Returns a dictionary with guild information.
    """
    guild = db.query(Guild).filter(Guild.id == guild_id).first()
    if not guild:
        return None

    next_level_xp = _get_xp_for_next_level(guild.level)
    current_level_xp = _get_xp_for_current_level(guild.level)
    xp_in_level = guild.total_xp - current_level_xp
    xp_needed = (next_level_xp - current_level_xp) if next_level_xp else xp_in_level
    progress = (xp_in_level / xp_needed * 100) if xp_needed > 0 else 100

    return {
        "id": guild.id,
        "name": guild.name,
        "tag": guild.tag,
        "emblem": guild.emblem,
        "owner_id": guild.owner_id,
        "chat_id": guild.chat_id,
        "level": guild.level,
        "total_xp": guild.total_xp,
        "guild_coins": guild.guild_coins,
        "member_count": guild.member_count,
        "created_at": guild.created_at.isoformat() if guild.created_at else None,
        "xp_progress": {
            "current_level_xp": current_level_xp,
            "next_level_xp": next_level_xp,
            "xp_in_level": xp_in_level,
            "xp_needed": xp_needed,
            "progress_percent": round(progress, 1),
        },
    }


def get_guild_leaderboard(db: Session, chat_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get top guilds by XP for a chat.
    Returns a list of guild dictionaries.
    """
    guilds = (
        db.query(Guild)
        .filter(Guild.chat_id == chat_id)
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
        })
    return result


def add_guild_xp(db: Session, guild_id: int, amount: int) -> Guild:
    """
    Add XP to a guild and auto-level it if threshold reached.
    Returns the updated Guild object.
    """
    guild = db.query(Guild).filter(Guild.id == guild_id).first()
    if not guild:
        raise ValueError(f"Guild {guild_id} not found.")

    old_level = guild.level
    guild.total_xp += amount
    new_level = _get_guild_level(guild.total_xp)

    leveled_up = False
    if new_level > old_level:
        guild.level = new_level
        leveled_up = True
        logger.info(
            f"Guild '{guild.name}' leveled up from {old_level} to {new_level}!"
        )

    db.commit()
    db.refresh(guild)
    guild._leveled_up = leveled_up
    guild._old_level = old_level
    return guild


def update_guild_rankings(db: Session) -> None:
    """
    Recalculate all guild rankings based on XP.
    Updates the ranking field on all guilds.
    """
    guilds = db.query(Guild).order_by(Guild.total_xp.desc()).all()
    for rank, guild in enumerate(guilds, 1):
        guild.ranking = rank
    db.commit()
    logger.info("All guild rankings recalculated.")


def get_guild_members(db: Session, guild_id: int) -> List[User]:
    """
    Get all members of a guild.
    Returns a list of User objects.
    """
    members = (
        db.query(User)
        .filter(User.guild_id == guild_id)
        .order_by(User.total_xp.desc())
        .all()
    )
    return members


def disband_guild(db: Session, guild_id: int, owner_id: int) -> bool:
    """
    Disband a guild. Only the owner can do this.
    All members are removed from the guild.
    Returns True if successful.
    """
    guild = db.query(Guild).filter(Guild.id == guild_id).first()
    if not guild:
        raise ValueError("Guild not found.")

    if guild.owner_id != owner_id:
        raise ValueError("Only the guild owner can disband the guild.")

    # Remove all members
    members = db.query(User).filter(User.guild_id == guild_id).all()
    for member in members:
        member.guild_id = None
        member.guild_name = None

    guild_name = guild.name
    db.delete(guild)
    db.commit()
    logger.info(f"Guild '{guild_name}' disbanded by owner {owner_id}")
    return True


def transfer_ownership(
    db: Session, guild_id: int, current_owner: int, new_owner: int
) -> Guild:
    """
    Transfer guild ownership to another member.
    Returns the updated Guild object.
    """
    guild = db.query(Guild).filter(Guild.id == guild_id).first()
    if not guild:
        raise ValueError("Guild not found.")

    if guild.owner_id != current_owner:
        raise ValueError("Only the current owner can transfer ownership.")

    new_owner_user = db.query(User).filter(User.user_id == new_owner).first()
    if not new_owner_user or new_owner_user.guild_id != guild_id:
        raise ValueError("New owner must be a member of this guild.")

    guild.owner_id = new_owner
    db.commit()
    db.refresh(guild)
    logger.info(
        f"Guild '{guild.name}' ownership transferred from {current_owner} to {new_owner}"
    )
    return guild


def set_guild_emblem(db: Session, guild_id: int, emblem: str) -> Guild:
    """
    Set the emblem/emoji for a guild.
    Returns the updated Guild object.
    """
    guild = db.query(Guild).filter(Guild.id == guild_id).first()
    if not guild:
        raise ValueError("Guild not found.")

    guild.emblem = emblem
    db.commit()
    db.refresh(guild)
    logger.info(f"Guild '{guild.name}' emblem set to '{emblem}'")
    return guild
