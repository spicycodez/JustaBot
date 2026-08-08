from __future__ import annotations

import logging
import re

from aiogram import Router, F
from aiogram.types import Message

from bot.config import settings
from bot.services.economy_service import economy_service
from bot.services.reputation_service import reputation_service

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def handle_group_message(message: Message) -> None:
    """Main handler for all group/supergroup messages."""
    try:
        user = message.from_user
        if user is None or user.is_bot:
            return

        chat_id = message.chat.id
        user_id = user.id
        username = user.username or user.first_name or "Anon"

        # 1. Get or create user
        await economy_service.get_or_create_user(user_id, chat_id, username)

        # 2. Check /start with referral args (in group context)
        if message.text and message.text.startswith("/start"):
            parts = message.text.split()
            if len(parts) > 1 and parts[1].startswith("ref_"):
                referrer_id = int(parts[1].split("_")[1])
                if referrer_id != user_id:
                    try:
                        await economy_service.process_referral(user_id, referrer_id)
                    except Exception:
                        pass

        # 3. Check ChatSettings is_enabled
        chat_settings = await economy_service.get_chat_settings(chat_id)
        if chat_settings and not chat_settings.is_enabled:
            return

        # 4. Handle text messages – XP award
        if message.text:
            # Skip commands (they are handled by command_router)
            if message.text.startswith("/"):
                return

            # Anti-spam check
            is_spam = await economy_service.anti_spam_check(user_id, chat_id)
            if is_spam:
                return

            leveled_up, new_level = await economy_service.award_message_xp(user_id, chat_id)
            if leveled_up and new_level:
                try:
                    await economy_service.check_achievements(user_id, chat_id)
                except Exception:
                    pass
                await message.reply(
                    f"\u2b50 <b>{username}</b> leveled up to <b>Level {new_level}</b>!"
                )

        # 5. Stickers & forwards – no XP, silently skip
        if message.sticker or message.forward_from or message.forward_from_chat:
            return

        # 6. Handle new_chat_members (welcome)
        if message.new_chat_members:
            for member in message.new_chat_members:
                if member.is_bot:
                    continue
                member_name = member.username or member.first_name or "User"
                try:
                    await economy_service.get_or_create_user(member.id, chat_id, member_name)
                except Exception:
                    pass
                welcome_text = (
                    f"✨ Welcome <b>{member_name}</b> to the group!\n"
                    f"🎮 Send messages to earn XP and level up!"
                )
                await message.reply(welcome_text)
            return

        # 7. Handle voice_chat_started
        if message.voice_chat_started:
            await economy_service.award_voice_xp(user_id, chat_id)
            return

    except Exception as e:
        logger.error("Error in handle_group_message: %s", e, exc_info=True)


@router.message(F.text.startswith("/thanks"))
async def handle_thanks(message: Message) -> None:
    """Handle /thanks @mention to give reputation."""
    try:
        user = message.from_user
        if user is None or user.is_bot:
            return

        text = message.text or ""
        # Parse @mention from the message
        mention_match = re.search(r"@(\w+)", text)
        if not mention_match:
            await message.reply("\u2753 Mention someone to thank: /thanks @username")
            return

        target_username = mention_match.group(1)
        giver_id = user.id
        chat_id = message.chat.id

        result = await reputation_service.give_thanks(giver_id, target_username, chat_id)
        await message.reply(result)

    except Exception as e:
        logger.error("Error in handle_thanks: %s", e, exc_info=True)
        await message.reply("\u274c An error occurred while processing your thanks.")
