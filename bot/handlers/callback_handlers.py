from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.services.economy_service import economy_service
from bot.services.admin_service import admin_service
from bot.utils.formatters import format_profile, format_quest_list, format_inventory
from bot.keyboards.profile import profile_keyboard
from bot.keyboards.quests import quest_keyboard
from bot.keyboards.daily import daily_reward_keyboard
from bot.keyboards.shop import shop_keyboard
from bot.keyboards.guild import guild_keyboard
from bot.keyboards.battle import battle_keyboard
from bot.keyboards.leaderboard import leaderboard_keyboard
from bot.keyboards.settings import settings_keyboard

logger = logging.getLogger(__name__)
router = Router()


# ==================================================================
# Profile callbacks  (profile_*)
# ==================================================================

@router.callback_query(F.data.startswith("profile_"))
async def cb_profile(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        data = callback.data
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id if callback.message else 0

        if data == "profile_main":
            text = await format_profile(user_id, chat_id)
            kb = profile_keyboard(user_id)
            await callback.message.edit_text(text, reply_markup=kb)

        elif data == "profile_xp":
            text = await economy_service.get_xp_info(user_id, chat_id)
            await callback.message.edit_text(text, reply_markup=profile_keyboard(user_id))

        elif data == "profile_coins":
            text = await economy_service.get_coins_info(user_id, chat_id)
            await callback.message.edit_text(text, reply_markup=profile_keyboard(user_id))

        elif data == "profile_achievements":
            text = await economy_service.get_achievements(user_id, chat_id)
            await callback.message.edit_text(text, reply_markup=profile_keyboard(user_id))

        elif data == "profile_stats":
            text = await economy_service.get_detailed_stats(user_id, chat_id)
            await callback.message.edit_text(text, reply_markup=profile_keyboard(user_id))

    except Exception as e:
        logger.error("Error in cb_profile: %s", e, exc_info=True)


# ==================================================================
# Shop callbacks  (shop_*)
# ==================================================================

@router.callback_query(F.data.startswith("shop_"))
async def cb_shop(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        data = callback.data
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id if callback.message else 0

        if data.startswith("shop_cat_"):
            category = data.split("_", 2)[2]
            text, kb = await economy_service.get_shop_page(user_id, chat_id, category=category)
            await callback.message.edit_text(text, reply_markup=kb)

        elif data.startswith("shop_item_"):
            item_id = data.split("_", 2)[2]
            text, kb = await economy_service.get_item_details(user_id, chat_id, item_id)
            await callback.message.edit_text(text, reply_markup=kb)

        elif data.startswith("shop_buy_"):
            item_id = data.split("_", 2)[2]
            text, kb = await economy_service.confirm_purchase(user_id, chat_id, item_id)
            if kb:
                await callback.message.edit_text(text, reply_markup=kb)
            else:
                await callback.message.edit_text(text)

        elif data == "shop_back":
            text, kb = await economy_service.get_shop_page(user_id, chat_id)
            await callback.message.edit_text(text, reply_markup=kb)

    except Exception as e:
        logger.error("Error in cb_shop: %s", e, exc_info=True)


# ==================================================================
# Quest callbacks  (quest_*)
# ==================================================================

@router.callback_query(F.data.startswith("quest_"))
async def cb_quest(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        data = callback.data
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id if callback.message else 0

        if data.startswith("quest_claim_"):
            quest_id = data.split("_", 2)[2]
            result = await economy_service.claim_quest_reward(user_id, chat_id, quest_id)
            await callback.message.edit_text(result, reply_markup=quest_keyboard(user_id))

        elif data == "quest_daily":
            text = await format_quest_list(user_id, chat_id, tab="daily")
            await callback.message.edit_text(text, reply_markup=quest_keyboard(user_id, tab="daily"))

        elif data == "quest_weekly":
            text = await format_quest_list(user_id, chat_id, tab="weekly")
            await callback.message.edit_text(text, reply_markup=quest_keyboard(user_id, tab="weekly"))

    except Exception as e:
        logger.error("Error in cb_quest: %s", e, exc_info=True)


# ==================================================================
# Guild callbacks  (guild_*)
# ==================================================================

@router.callback_query(F.data.startswith("guild_"))
async def cb_guild(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        data = callback.data
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id if callback.message else 0

        if data == "guild_create":
            text, kb = await economy_service.init_guild_creation(user_id, chat_id)
            if kb:
                await callback.message.edit_text(text, reply_markup=kb)
            else:
                await callback.message.edit_text(text)

        elif data == "guild_join":
            text, kb = await economy_service.get_guild_join_menu(user_id, chat_id)
            if kb:
                await callback.message.edit_text(text, reply_markup=kb)
            else:
                await callback.message.edit_text(text)

        elif data == "guild_leave":
            result = await economy_service.leave_guild(user_id, chat_id)
            await callback.message.edit_text(result, reply_markup=guild_keyboard(user_id, chat_id))

        elif data == "guild_info":
            info = await economy_service.get_guild_info(user_id, chat_id)
            kb = guild_keyboard(user_id, chat_id)
            await callback.message.edit_text(info, reply_markup=kb)

        elif data.startswith("guild_join_"):
            guild_id = data.split("_", 2)[2]
            result = await economy_service.join_guild(user_id, chat_id, guild_id)
            await callback.message.edit_text(result, reply_markup=guild_keyboard(user_id, chat_id))

    except Exception as e:
        logger.error("Error in cb_guild: %s", e, exc_info=True)


# ==================================================================
# Battle callbacks  (battle_*)
# ==================================================================

@router.callback_query(F.data.startswith("battle_"))
async def cb_battle(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        data = callback.data
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id if callback.message else 0

        if data == "battle_join":
            result = await economy_service.join_battle(user_id, chat_id)
            await callback.message.edit_text(result, reply_markup=battle_keyboard(user_id, chat_id))

        elif data == "battle_info":
            info = await economy_service.get_battle_info(user_id, chat_id)
            await callback.message.edit_text(info, reply_markup=battle_keyboard(user_id, chat_id))

        elif data == "battle_refresh":
            info = await economy_service.get_battle_info(user_id, chat_id)
            await callback.message.edit_text(info, reply_markup=battle_keyboard(user_id, chat_id))

    except Exception as e:
        logger.error("Error in cb_battle: %s", e, exc_info=True)


# ==================================================================
# Daily callbacks  (daily_*)
# ==================================================================

@router.callback_query(F.data.startswith("daily_"))
async def cb_daily(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        data = callback.data
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id if callback.message else 0

        if data == "daily_claim":
            result = await economy_service.claim_daily_reward(user_id, chat_id)
            kb = daily_reward_keyboard(user_id)
            await callback.message.edit_text(result, reply_markup=kb)

        elif data == "daily_streak":
            info = await economy_service.get_streak_info(user_id, chat_id)
            kb = daily_reward_keyboard(user_id)
            await callback.message.edit_text(info, reply_markup=kb)

    except Exception as e:
        logger.error("Error in cb_daily: %s", e, exc_info=True)


# ==================================================================
# Leaderboard callbacks  (lb_*)
# ==================================================================

@router.callback_query(F.data.startswith("lb_"))
async def cb_leaderboard(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        data = callback.data
        chat_id = callback.message.chat.id if callback.message else 0

        # Format: lb_{type}_{page}
        # e.g. lb_xp_0, lb_coins_1, lb_streak_0, lb_helpers_0, lb_invites_0, lb_guilds_0
        parts = data.split("_")
        lb_type = parts[1] if len(parts) > 1 else "xp"
        page = int(parts[2]) if len(parts) > 2 else 0

        valid_types = ("xp", "coins", "streak", "helpers", "invites", "guilds")
        if lb_type not in valid_types:
            lb_type = "xp"

        text, kb = await economy_service.get_leaderboard(chat_id, lb_type, page)
        await callback.message.edit_text(text, reply_markup=kb)

    except Exception as e:
        logger.error("Error in cb_leaderboard: %s", e, exc_info=True)


# ==================================================================
# Settings callbacks  (settings_*)
# ==================================================================

@router.callback_query(F.data.startswith("settings_"))
async def cb_settings(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        data = callback.data
        chat_id = callback.message.chat.id if callback.message else 0

        setting_key = data.split("_", 1)[1] if "_" in data else ""
        if not setting_key:
            return

        result = await admin_service.toggle_setting(chat_id, setting_key)
        kb = await admin_service.get_settings_keyboard(chat_id)
        await callback.message.edit_text(result, reply_markup=kb)

    except Exception as e:
        logger.error("Error in cb_settings: %s", e, exc_info=True)


# ==================================================================
# Confirm callbacks  (confirm_*)
# ==================================================================

@router.callback_query(F.data.startswith("confirm_"))
async def cb_confirm(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        data = callback.data
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id if callback.message else 0

        # Format: confirm_{action}_{target_id_or_item_id}
        parts = data.split("_", 2)
        action = parts[1] if len(parts) > 1 else ""
        target = parts[2] if len(parts) > 2 else ""

        if action == "buy":
            result = await economy_service.execute_purchase(user_id, chat_id, target)
            await callback.message.edit_text(result)

        elif action == "cancel":
            await callback.message.edit_text("❌ Action cancelled.")

        elif action == "join_guild":
            result = await economy_service.join_guild(user_id, chat_id, target)
            await callback.message.edit_text(result)

        elif action == "leave_guild":
            result = await economy_service.leave_guild(user_id, chat_id)
            await callback.message.edit_text(result)

        elif action == "create_guild":
            result = await economy_service.create_guild(user_id, chat_id, target)
            await callback.message.edit_text(result)

    except Exception as e:
        logger.error("Error in cb_confirm: %s", e, exc_info=True)


# ==================================================================
# Minigame callbacks  (minigame_*)
# ==================================================================

@router.callback_query(F.data.startswith("minigame_"))
async def cb_minigame(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        data = callback.data
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id if callback.message else 0

        if data.startswith("minigame_rps_"):
            choice = data.split("_", 2)[2]
            from bot.services.minigames_service import minigames_service
            result = await minigames_service.process_rps_choice(user_id, chat_id, choice)
            if isinstance(result, tuple):
                text, kb = result
                await callback.message.edit_text(text, reply_markup=kb)
            else:
                await callback.message.edit_text(result)

        elif data.startswith("minigame_trivia_"):
            answer = data.split("_", 2)[2]
            from bot.services.minigames_service import minigames_service
            result = await minigames_service.process_trivia_answer(user_id, chat_id, answer)
            if isinstance(result, tuple):
                text, kb = result
                await callback.message.edit_text(text, reply_markup=kb)
            else:
                await callback.message.edit_text(result)

    except Exception as e:
        logger.error("Error in cb_minigame: %s", e, exc_info=True)
