"""Display formatters for profiles, leaderboards, guilds, quests, battles, shop, and inventory."""

from __future__ import annotations

from bot.utils.helpers import format_number, format_xp_bar
from bot.services.streak_service import format_streak
from bot.services.level_service import xp_required


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

def format_profile(user) -> str:
    """Build a rich text profile card for *user*."""
    name = getattr(user, "username", None) or getattr(user, "first_name", None) or f"User #{user.telegram_id}"
    level = user.level or 1
    xp = user.xp or 0
    needed = xp_required(level)
    prev_total = sum(int(100 * (i ** 1.5)) for i in range(1, level))
    current_in_level = max(xp - prev_total, 0)
    rank = getattr(user, "rank", None) or "Newcomer"
    coins = format_number(user.coins or 0)
    rep = user.reputation or 0
    streak = user.streak or 0
    streak_icon = format_streak(streak)
    achievements = user.achievements or []
    guild = getattr(user, "guild_id", None)

    lines = [
        f"👤 <b>{name}</b>",
        f"🏷 <b>{rank}</b>  •  Level {level}",
        f"{format_xp_bar(current_in_level, needed)}  {xp:,} XP",
        "",
        f"💰 Coins: {coins}",
        f"⭐ Reputation: {rep}",
    ]

    if streak > 0:
        lines.append(f"{streak_icon} Streak: {streak} day{'s' if streak != 1 else ''}")

    if guild:
        lines.append(f"🏰 Guild: {guild}")

    if achievements:
        lines.append(f"🏆 Achievements: {len(achievements)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

_MEDALS = ["🥇", "🥈", "🥉"]


def format_leaderboard(users: list[dict], title: str, category: str = "xp") -> str:
    """Build a leaderboard message.

    *users* is a list of dicts with at least ``telegram_id``, ``username``,
    and a value matching *category* (``xp``, ``coins``, ``reputation``).
    """
    lines = [f"🏆 <b>{title}</b>\n"]
    for idx, u in enumerate(users):
        medal = _MEDALS[idx] if idx < 3 else f"{idx + 1}."
        name = u.get("username") or f"User #{u['telegram_id']}"
        if category == "xp":
            val = format_number(u.get("xp", u.get("total_xp", 0)))
            lines.append(f"{medal} <b>{name}</b> — {val} XP")
        elif category == "coins":
            val = format_number(u.get("coins", 0))
            lines.append(f"{medal} <b>{name}</b> — {val} 💰")
        elif category == "reputation":
            val = format_number(u.get("reputation", 0))
            lines.append(f"{medal} <b>{name}</b> — {val} ⭐")
        else:
            lines.append(f"{medal} <b>{name}</b>")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Guild
# ---------------------------------------------------------------------------

def format_guild_info(guild) -> str:
    """Build a guild information card."""
    name = getattr(guild, "name", "Unknown")
    level = getattr(guild, "level", 1)
    members = getattr(guild, "member_count", 0)
    xp = getattr(guild, "total_xp", 0)
    owner = getattr(guild, "owner_username", "Unknown")

    lines = [
        f"🏰 <b>{name}</b>",
        f"Level {level}  •  {members} members",
        f"Total XP: {format_number(xp)}",
        f"Owner: {owner}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Quests
# ---------------------------------------------------------------------------

def format_quest_list(quests: list) -> str:
    """Build a quest list with progress bars."""
    lines = ["📜 <b>Quests</b>\n"]
    for q in quests:
        target = getattr(q, "target", 0) or 0
        progress = min(getattr(q, "progress", 0) or 0, target)
        pct = int((progress / target) * 100) if target else 0
        bar = format_xp_bar(progress, target, width=8)
        status = "✅" if getattr(q, "is_completed", False) else ("🎁" if getattr(q, "claimed", False) else "⬜")
        qname = getattr(q, "quest_id", q).replace("_", " ").title()
        lines.append(f"{status} <b>{qname}</b>  {bar}  {pct}%")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Battle
# ---------------------------------------------------------------------------

def format_battle_score(battle) -> str:
    """Build a battle scoreboard."""
    lines = ["⚔️ <b>Battle Results</b>\n"]
    scores = getattr(battle, "scores", {})
    for name, score in scores.items():
        lines.append(f"  {name}: {score} pts")
    winner = getattr(battle, "winner", None)
    if winner:
        lines.append(f"\n🏆 Winner: <b>{winner}</b>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Shop
# ---------------------------------------------------------------------------

def format_shop_item(item) -> str:
    """Build a single shop-item display."""
    name = getattr(item, "name", "Unknown")
    price = getattr(item, "price", 0)
    desc = getattr(item, "description", "")
    icon = getattr(item, "icon", "📦")
    rarity = getattr(item, "rarity", "")
    line = f"{icon} <b>{name}</b>  —  {format_number(price)} 💰"
    if rarity:
        line += f"  [{rarity}]"
    if desc:
        line += f"\n   {desc}"
    return line


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

def format_inventory(items: list) -> str:
    """Build an inventory listing."""
    if not items:
        return "🎒 Your inventory is empty."
    lines = ["🎒 <b>Inventory</b>\n"]
    for item in items:
        name = getattr(item, "name", str(item))
        icon = getattr(item, "icon", "📦")
        qty = getattr(item, "quantity", 1)
        lines.append(f"{icon} {name}" + (f" ×{qty}" if qty > 1 else ""))
    return "\n".join(lines)
