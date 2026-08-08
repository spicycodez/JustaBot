import logging
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from bot.models.guild import Guild
from bot.models.user import User
from bot.models.guild_battle import GuildBattle

logger = logging.getLogger(__name__)

BATTLE_WINNER_GUILD_COINS = 500
BATTLE_WINNER_XP_PER_MEMBER = 200
BATTLE_LOSER_XP_PER_MEMBER = 50
BATTLE_DRAW_XP_PER_MEMBER = 100
LEVEL_MATCH_RANGE = 2  # Max level difference for auto-matching


def create_battle(db: Session, guild_a_id: int, guild_b_id: int) -> GuildBattle:
    """
    Create a new guild battle between two guilds.
    Returns the created GuildBattle object.
    """
    guild_a = db.query(Guild).filter(Guild.id == guild_a_id).first()
    guild_b = db.query(Guild).filter(Guild.id == guild_b_id).first()

    if not guild_a:
        raise ValueError(f"Guild A ({guild_a_id}) not found.")
    if not guild_b:
        raise ValueError(f"Guild B ({guild_b_id}) not found.")
    if guild_a_id == guild_b_id:
        raise ValueError("Cannot create a battle between the same guild.")

    # Check for existing active battles
    active_a = (
        db.query(GuildBattle)
        .filter(
            GuildBattle.guild_a_id == guild_a_id,
            GuildBattle.status == "active",
        )
        .first()
    )
    if active_a:
        raise ValueError(f"Guild A is already in an active battle.")

    active_b = (
        db.query(GuildBattle)
        .filter(
            GuildBattle.guild_b_id == guild_b_id,
            GuildBattle.status == "active",
        )
        .first()
    )
    if active_b:
        raise ValueError(f"Guild B is already in an active battle.")

    battle = GuildBattle(
        guild_a_id=guild_a_id,
        guild_b_id=guild_b_id,
        score_a=0,
        score_b=0,
        status="pending",
        created_at=datetime.utcnow(),
    )
    db.add(battle)
    db.commit()
    db.refresh(battle)

    logger.info(
        f"Battle created: {guild_a.name} vs {guild_b.name} (id={battle.id})"
    )
    return battle


def start_battle(db: Session, battle_id: int) -> GuildBattle:
    """
    Start a pending battle (change status to 'active').
    Returns the updated GuildBattle.
    """
    battle = db.query(GuildBattle).filter(GuildBattle.id == battle_id).first()
    if not battle:
        raise ValueError(f"Battle {battle_id} not found.")

    if battle.status != "pending":
        raise ValueError(f"Cannot start battle with status '{battle.status}'.")

    battle.status = "active"
    battle.started_at = datetime.utcnow()
    db.commit()
    db.refresh(battle)

    logger.info(f"Battle {battle_id} started.")
    return battle


def update_battle_score(
    db: Session, battle_id: int, guild_side: str, points: int
) -> GuildBattle:
    """
    Add points to a guild's score in a battle.
    guild_side must be 'a' or 'b'.
    Returns the updated GuildBattle.
    """
    battle = db.query(GuildBattle).filter(GuildBattle.id == battle_id).first()
    if not battle:
        raise ValueError(f"Battle {battle_id} not found.")

    if battle.status != "active":
        raise ValueError(f"Cannot update score for battle with status '{battle.status}'.")

    if guild_side == "a":
        battle.score_a += points
    elif guild_side == "b":
        battle.score_b += points
    else:
        raise ValueError("guild_side must be 'a' or 'b'.")

    db.commit()
    db.refresh(battle)
    return battle


def end_battle(db: Session, battle_id: int) -> Dict[str, Any]:
    """
    End a battle and determine the winner.
    Rewards:
      Winner guild: 500 guild coins + 200 XP per member
      Loser guild: 50 XP per member
      Draw: 100 XP per member each
    Returns a summary dictionary.
    """
    battle = db.query(GuildBattle).filter(GuildBattle.id == battle_id).first()
    if not battle:
        raise ValueError(f"Battle {battle_id} not found.")

    if battle.status != "active":
        raise ValueError(f"Cannot end battle with status '{battle.status}'.")

    battle.status = "completed"
    battle.ended_at = datetime.utcnow()

    guild_a = db.query(Guild).filter(Guild.id == battle.guild_a_id).first()
    guild_b = db.query(Guild).filter(Guild.id == battle.guild_b_id).first()

    members_a = (
        db.query(User).filter(User.guild_id == battle.guild_a_id).all()
    )
    members_b = (
        db.query(User).filter(User.guild_id == battle.guild_b_id).all()
    )

    # Determine winner
    if battle.score_a > battle.score_b:
        winner_guild = guild_a
        winner_members = members_a
        loser_members = members_b
        result = "a_wins"
    elif battle.score_b > battle.score_a:
        winner_guild = guild_b
        winner_members = members_b
        loser_members = members_a
        result = "b_wins"
    else:
        winner_guild = None
        winner_members = []
        loser_members = []
        result = "draw"

    # Distribute rewards
    rewards = []

    if result == "draw":
        # Both guilds get 100 XP per member
        for member in members_a + members_b:
            member.total_xp += BATTLE_DRAW_XP_PER_MEMBER
            member.season_xp += BATTLE_DRAW_XP_PER_MEMBER
            rewards.append({
                "user_id": member.user_id,
                "guild_side": "a" if member.guild_id == battle.guild_a_id else "b",
                "xp_awarded": BATTLE_DRAW_XP_PER_MEMBER,
                "result": "draw",
            })
    else:
        # Winner guild gets coins + XP
        winner_guild.guild_coins += BATTLE_WINNER_GUILD_COINS

        for member in winner_members:
            member.total_xp += BATTLE_WINNER_XP_PER_MEMBER
            member.season_xp += BATTLE_WINNER_XP_PER_MEMBER
            member.guild_battles_won = (member.guild_battles_won or 0) + 1
            rewards.append({
                "user_id": member.user_id,
                "guild_side": "a" if member.guild_id == battle.guild_a_id else "b",
                "xp_awarded": BATTLE_WINNER_XP_PER_MEMBER,
                "result": "won",
            })

        # Loser guild gets consolation XP
        for member in loser_members:
            member.total_xp += BATTLE_LOSER_XP_PER_MEMBER
            member.season_xp += BATTLE_LOSER_XP_PER_MEMBER
            rewards.append({
                "user_id": member.user_id,
                "guild_side": "a" if member.guild_id == battle.guild_a_id else "b",
                "xp_awarded": BATTLE_LOSER_XP_PER_MEMBER,
                "result": "lost",
            })

    db.commit()
    db.refresh(battle)

    summary = {
        "battle_id": battle.id,
        "guild_a": {
            "id": guild_a.id if guild_a else None,
            "name": guild_a.name if guild_a else None,
            "tag": guild_a.tag if guild_a else None,
            "score": battle.score_a,
        },
        "guild_b": {
            "id": guild_b.id if guild_b else None,
            "name": guild_b.name if guild_b else None,
            "tag": guild_b.tag if guild_b else None,
            "score": battle.score_b,
        },
        "result": result,
        "winner_guild_name": winner_guild.name if winner_guild else None,
        "winner_guild_coins": BATTLE_WINNER_GUILD_COINS if winner_guild else 0,
        "rewards": rewards,
        "ended_at": battle.ended_at.isoformat() if battle.ended_at else None,
    }

    logger.info(f"Battle {battle_id} ended. Result: {result}")
    return summary


def get_active_battles(db: Session) -> List[Dict[str, Any]]:
    """
    Get all currently active battles.
    Returns a list of battle dictionaries.
    """
    battles = (
        db.query(GuildBattle)
        .filter(GuildBattle.status == "active")
        .all()
    )

    result = []
    for b in battles:
        guild_a = db.query(Guild).filter(Guild.id == b.guild_a_id).first()
        guild_b = db.query(Guild).filter(Guild.id == b.guild_b_id).first()

        result.append({
            "id": b.id,
            "guild_a": {
                "id": b.guild_a_id,
                "name": guild_a.name if guild_a else "Unknown",
                "tag": guild_a.tag if guild_a else "?",
                "score": b.score_a,
            },
            "guild_b": {
                "id": b.guild_b_id,
                "name": guild_b.name if guild_b else "Unknown",
                "tag": guild_b.tag if guild_b else "?",
                "score": b.score_b,
            },
            "status": b.status,
            "started_at": b.started_at.isoformat() if b.started_at else None,
        })

    return result


def get_battle_info(db: Session, battle_id: int) -> Optional[Dict[str, Any]]:
    """
    Get detailed info about a specific battle.
    Returns a battle dictionary or None.
    """
    battle = db.query(GuildBattle).filter(GuildBattle.id == battle_id).first()
    if not battle:
        return None

    guild_a = db.query(Guild).filter(Guild.id == battle.guild_a_id).first()
    guild_b = db.query(Guild).filter(Guild.id == battle.guild_b_id).first()

    return {
        "id": battle.id,
        "guild_a": {
            "id": battle.guild_a_id,
            "name": guild_a.name if guild_a else "Unknown",
            "tag": guild_a.tag if guild_a else "?",
            "level": guild_a.level if guild_a else 0,
            "score": battle.score_a,
        },
        "guild_b": {
            "id": battle.guild_b_id,
            "name": guild_b.name if guild_b else "Unknown",
            "tag": guild_b.tag if guild_b else "?",
            "level": guild_b.level if guild_b else 0,
            "score": battle.score_b,
        },
        "status": battle.status,
        "created_at": battle.created_at.isoformat() if battle.created_at else None,
        "started_at": battle.started_at.isoformat() if battle.started_at else None,
        "ended_at": battle.ended_at.isoformat() if battle.ended_at else None,
    }


def auto_match_guilds(db: Session) -> Optional[Dict[str, Any]]:
    """
    Automatically match two similar-level guilds for a battle.
    Finds guilds within LEVEL_MATCH_RANGE levels of each other
    that are not already in an active battle.
    Returns match info or None if no match found.
    """
    # Get guilds not in active battles
    active_battle_guild_ids = set()
    active_battles = db.query(GuildBattle).filter(GuildBattle.status == "active").all()
    for ab in active_battles:
        active_battle_guild_ids.add(ab.guild_a_id)
        active_battle_guild_ids.add(ab.guild_b_id)

    available_guilds = (
        db.query(Guild)
        .filter(Guild.id.notin_(active_battle_guild_ids))
        .order_by(Guild.level)
        .all()
    )

    if len(available_guilds) < 2:
        return None

    # Sort by level and find closest match
    available_guilds.sort(key=lambda g: g.level)

    best_match = None
    best_diff = float("inf")

    for i in range(len(available_guilds) - 1):
        g1 = available_guilds[i]
        g2 = available_guilds[i + 1]
        diff = abs(g1.level - g2.level)

        if diff <= LEVEL_MATCH_RANGE and diff < best_diff:
            best_diff = diff
            best_match = (g1, g2)

    if not best_match:
        # Fallback: pick two random guilds
        if len(available_guilds) >= 2:
            pair = random.sample(available_guilds, 2)
            best_match = (pair[0], pair[1])
        else:
            return None

    g1, g2 = best_match
    battle = create_battle(db, g1.id, g2.id)

    return {
        "battle_id": battle.id,
        "guild_a": {"id": g1.id, "name": g1.name, "tag": g1.tag, "level": g1.level},
        "guild_b": {"id": g2.id, "name": g2.name, "tag": g2.tag, "level": g2.level},
        "level_difference": abs(g1.level - g2.level),
    }
