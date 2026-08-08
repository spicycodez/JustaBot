from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.types import Message

from bot.config import settings
from bot.services.economy_service import economy_service
from bot.services.admin_service import admin_service

logger = logging.getLogger(__name__)
router = Router()


async def _is_admin(message: Message) -> bool:
    """Check if the message sender is a bot admin or chat admin."""
    user = message.from_user
    if user is None:
        return False
    if user.id in settings.ADMIN_IDS:
        return True
    # Check chat admin status for group chats
    if message.chat.type in ("group", "supergroup"):
        try:
            member = await message.bot.get_chat_member(message.chat.id, user.id)
            if member.status in ("administrator", "creator"):
                return True
        except Exception:
            pass
    return False


@router.message(F.text.startswith("/settings"))
async def cmd_settings(message: Message) -> None:
    try:
        if not await _is_admin(message):
            await message.answer("⛔ Admin only.")
            return
        chat_id = message.chat.id
        settings_text = await admin_service.get_settings_text(chat_id)
        kb = await admin_service.get_settings_keyboard(chat_id)
        await message.answer(settings_text, reply_markup=kb)
    except Exception as e:
        logger.error("Error in cmd_settings: %s", e, exc_info=True)


@router.message(F.text.startswith("/addxp"))
async def cmd_addxp(message: Message) -> None:
    try:
        if not await _is_admin(message):
            return
        parts = message.text.split()
        if len(parts) < 3:
            await message.answer("❓ Usage: /addxp <user_id> <amount>")
            return
        user_id = int(parts[1])
        amount = int(parts[2])
        await economy_service.add_xp(user_id, message.chat.id, amount)
        await message.answer(f"✅ Added <b>{amount}</b> XP to user {user_id}.")
    except Exception as e:
        logger.error("Error in cmd_addxp: %s", e, exc_info=True)
        await message.answer("❌ Invalid arguments.")


@router.message(F.text.startswith("/removexp"))
async def cmd_removexp(message: Message) -> None:
    try:
        if not await _is_admin(message):
            return
        parts = message.text.split()
        if len(parts) < 3:
            await message.answer("❓ Usage: /removexp <user_id> <amount>")
            return
        user_id = int(parts[1])
        amount = int(parts[2])
        await economy_service.remove_xp(user_id, message.chat.id, amount)
        await message.answer(f"✅ Removed <b>{amount}</b> XP from user {user_id}.")
    except Exception as e:
        logger.error("Error in cmd_removexp: %s", e, exc_info=True)
        await message.answer("❌ Invalid arguments.")


@router.message(F.text.startswith("/addcoins"))
async def cmd_addcoins(message: Message) -> None:
    try:
        if not await _is_admin(message):
            return
        parts = message.text.split()
        if len(parts) < 3:
            await message.answer("❓ Usage: /addcoins <user_id> <amount>")
            return
        user_id = int(parts[1])
        amount = int(parts[2])
        await economy_service.add_coins(user_id, message.chat.id, amount)
        await message.answer(f"✅ Added <b>{amount}</b> coins to user {user_id}.")
    except Exception as e:
        logger.error("Error in cmd_addcoins: %s", e, exc_info=True)
        await message.answer("❌ Invalid arguments.")


@router.message(F.text.startswith("/createquest"))
async def cmd_createquest(message: Message) -> None:
    try:
        if not await _is_admin(message):
            return
        result = await admin_service.init_quest_creation(message.from_user.id, message.chat.id)
        await message.answer(result)
    except Exception as e:
        logger.error("Error in cmd_createquest: %s", e, exc_info=True)


@router.message(F.text.startswith("/createevent"))
async def cmd_createevent(message: Message) -> None:
    try:
        if not await _is_admin(message):
            return
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer("❓ Usage: /createevent <type> <title>")
            return
        event_type = parts[1]
        title = parts[2]
        result = await admin_service.create_event(message.chat.id, event_type, title)
        await message.answer(result)
    except Exception as e:
        logger.error("Error in cmd_createevent: %s", e, exc_info=True)


@router.message(F.text.startswith("/endevent"))
async def cmd_endevent(message: Message) -> None:
    try:
        if not await _is_admin(message):
            return
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❓ Usage: /endevent <event_id>")
            return
        event_id = int(parts[1])
        result = await admin_service.end_event(event_id, message.chat.id)
        await message.answer(result)
    except Exception as e:
        logger.error("Error in cmd_endevent: %s", e, exc_info=True)


@router.message(F.text.startswith("/resetseason"))
async def cmd_resetseason(message: Message) -> None:
    try:
        if not await _is_admin(message):
            return
        if message.from_user.id not in settings.ADMIN_IDS:
            await message.answer("⛔ Bot admin only.")
            return
        result = await admin_service.reset_season(message.chat.id)
        await message.answer(result)
    except Exception as e:
        logger.error("Error in cmd_resetseason: %s", e, exc_info=True)


@router.message(F.text.startswith("/createguild"))
async def cmd_createguild(message: Message) -> None:
    try:
        if not await _is_admin(message):
            return
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer("❓ Usage: /createguild <name> <tag>")
            return
        name = parts[1]
        tag = parts[2]
        result = await admin_service.create_guild(message.chat.id, name, tag)
        await message.answer(result)
    except Exception as e:
        logger.error("Error in cmd_createguild: %s", e, exc_info=True)


@router.message(F.text.startswith("/givebadge"))
async def cmd_givebadge(message: Message) -> None:
    try:
        if not await _is_admin(message):
            return
        parts = message.text.split()
        if len(parts) < 3:
            await message.answer("❓ Usage: /givebadge <user_id> <badge_id>")
            return
        user_id = int(parts[1])
        badge_id = parts[2]
        result = await admin_service.give_badge(user_id, message.chat.id, badge_id)
        await message.answer(result)
    except Exception as e:
        logger.error("Error in cmd_givebadge: %s", e, exc_info=True)


@router.message(F.text.startswith("/banxp"))
async def cmd_banxp(message: Message) -> None:
    try:
        if not await _is_admin(message):
            return
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❓ Usage: /banxp <user_id>")
            return
        user_id = int(parts[1])
        await economy_service.ban_xp(user_id, message.chat.id)
        await message.answer(f"⛔ User {user_id} XP gain has been banned.")
    except Exception as e:
        logger.error("Error in cmd_banxp: %s", e, exc_info=True)


@router.message(F.text.startswith("/unbanxp"))
async def cmd_unbanxp(message: Message) -> None:
    try:
        if not await _is_admin(message):
            return
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❓ Usage: /unbanxp <user_id>")
            return
        user_id = int(parts[1])
        await economy_service.unban_xp(user_id, message.chat.id)
        await message.answer(f"✅ User {user_id} XP gain has been unbanned.")
    except Exception as e:
        logger.error("Error in cmd_unbanxp: %s", e, exc_info=True)


@router.message(F.text.startswith("/setxp"))
async def cmd_setxp(message: Message) -> None:
    try:
        if not await _is_admin(message):
            return
        parts = message.text.split()
        if len(parts) < 3:
            await message.answer("❓ Usage: /setxp <user_id> <amount>")
            return
        user_id = int(parts[1])
        amount = int(parts[2])
        await economy_service.set_xp(user_id, message.chat.id, amount)
        await message.answer(f"✅ Set XP to <b>{amount}</b> for user {user_id}.")
    except Exception as e:
        logger.error("Error in cmd_setxp: %s", e, exc_info=True)
        await message.answer("❌ Invalid arguments.")


@router.message(F.text.startswith("/setlevel"))
async def cmd_setlevel(message: Message) -> None:
    try:
        if not await _is_admin(message):
            return
        parts = message.text.split()
        if len(parts) < 3:
            await message.answer("❓ Usage: /setlevel <user_id> <level>")
            return
        user_id = int(parts[1])
        level = int(parts[2])
        await economy_service.set_level(user_id, message.chat.id, level)
        await message.answer(f"✅ Set level to <b>{level}</b> for user {user_id}.")
    except Exception as e:
        logger.error("Error in cmd_setlevel: %s", e, exc_info=True)
        await message.answer("❌ Invalid arguments.")


@router.message(F.text.startswith("/givereward"))
async def cmd_givereward(message: Message) -> None:
    try:
        if not await _is_admin(message):
            return
        parts = message.text.split()
        if len(parts) < 3:
            await message.answer("❓ Usage: /givereward <user_id> <item_id>")
            return
        user_id = int(parts[1])
        item_id = parts[2]
        result = await admin_service.give_reward(user_id, message.chat.id, item_id)
        await message.answer(result)
    except Exception as e:
        logger.error("Error in cmd_givereward: %s", e, exc_info=True)
