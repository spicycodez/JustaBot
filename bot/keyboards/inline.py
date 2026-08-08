from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

def profile_keyboard(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Stats", callback_data=f"stats:{user_id}")
    kb.button(text="🏆 Achievements", callback_data=f"achievements:{user_id}")
    kb.button(text="📦 Inventory", callback_data=f"inventory:{user_id}")
    kb.button(text="📜 Quests", callback_data="quests:view")
    kb.adjust(2, 2)
    return kb.as_markup()


# ---------------------------------------------------------------------------
# Shop
# ---------------------------------------------------------------------------

def shop_keyboard(category: str = "general") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 General", callback_data="shop:general")
    kb.button(text="⚔️ Battle", callback_data="shop:battle")
    kb.button(text="🏰 Guild", callback_data="shop:guild")
    kb.button(text="✨ Powers", callback_data="shop:powers")
    kb.button(text="🔙 Back", callback_data="menu:main")
    kb.adjust(2, 2, 1)
    # Highlight current category
    return kb.as_markup()


# ---------------------------------------------------------------------------
# Quests
# ---------------------------------------------------------------------------

def quest_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Daily", callback_data="quests:daily")
    kb.button(text="📅 Weekly", callback_data="quests:weekly")
    kb.button(text="🌟 Season", callback_data="quests:season")
    kb.button(text="🔙 Back", callback_data="menu:main")
    kb.adjust(3, 1)
    return kb.as_markup()


# ---------------------------------------------------------------------------
# Guild
# ---------------------------------------------------------------------------

def guild_keyboard(guild_id: str | None = None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if guild_id:
        kb.button(text="👥 Members", callback_data=f"guild:members:{guild_id}")
        kb.button(text="📊 Guild Stats", callback_data=f"guild:stats:{guild_id}")
        kb.button(text="⚔️ Guild Battles", callback_data=f"guild:battles:{guild_id}")
        kb.button(text="🚪 Leave Guild", callback_data=f"guild:leave:{guild_id}")
        kb.adjust(2, 2)
    else:
        kb.button(text="🏰 Create Guild", callback_data="guild:create")
        kb.button(text="🔍 Find Guild", callback_data="guild:find")
        kb.button(text="🔙 Back", callback_data="menu:main")
        kb.adjust(2, 1)
    return kb.as_markup()


# ---------------------------------------------------------------------------
# Battle
# ---------------------------------------------------------------------------

def battle_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⚔️ Quick Match", callback_data="battle:quick")
    kb.button(text="🏆 Ranked", callback_data="battle:ranked")
    kb.button(text="🏰 Guild Battle", callback_data="battle:guild")
    kb.button(text="🔙 Back", callback_data="menu:main")
    kb.adjust(2, 2)
    return kb.as_markup()


# ---------------------------------------------------------------------------
# Settings (admin / chat)
# ---------------------------------------------------------------------------

def settings_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Enable Bot", callback_data=f"settings:enable:{chat_id}")
    kb.button(text="❌ Disable Bot", callback_data=f"settings:disable:{chat_id}")
    kb.button(text="✖ XP Multiplier", callback_data=f"settings:xp_mult:{chat_id}")
    kb.button(text="🔙 Back", callback_data="menu:main")
    kb.adjust(2, 2)
    return kb.as_markup()


# ---------------------------------------------------------------------------
# Daily Reward
# ---------------------------------------------------------------------------

def daily_reward_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Claim Daily", callback_data="daily:claim")
    kb.button(text="🔙 Back", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


# ---------------------------------------------------------------------------
# Minigames
# ---------------------------------------------------------------------------

def minigames_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎲 Dice", callback_data="game:dice")
    kb.button(text="🃏 Cards", callback_data="game:cards")
    kb.button(text="🔢 Guess Number", callback_data="game:guess")
    kb.button(text="🧠 Trivia", callback_data="game:trivia")
    kb.button(text="🔙 Back", callback_data="menu:main")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


# ---------------------------------------------------------------------------
# Confirmation
# ---------------------------------------------------------------------------

def confirmation_keyboard(action: str, confirm_text: str = "✅ Confirm", cancel_text: str = "❌ Cancel") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=confirm_text, callback_data=f"confirm:{action}")
    kb.button(text=cancel_text, callback_data=f"cancel:{action}")
    kb.adjust(2)
    return kb.as_markup()


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

def pagination_keyboard(
    base_callback: str,
    current_page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if current_page > 1:
        kb.button(text="⬅ Prev", callback_data=f"{base_callback}:{current_page - 1}")
    if current_page < total_pages:
        kb.button(text="Next ➡", callback_data=f"{base_callback}:{current_page + 1}")
    kb.button(text="🔙 Back", callback_data="menu:main")
    row_sizes = [2] if (current_page > 1 and current_page < total_pages) else [1, 1]
    kb.adjust(*row_sizes)
    return kb.as_markup()
