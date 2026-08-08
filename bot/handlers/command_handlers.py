from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.types import Message

from bot.config import settings
from bot.services.economy_service import economy_service
from bot.services.minigames_service import minigames_service
from bot.keyboards.main_menu import main_menu_keyboard
from bot.keyboards.profile import profile_keyboard
from bot.keyboards.quests import quest_keyboard
from bot.keyboards.daily import daily_reward_keyboard
from bot.keyboards.shop import shop_keyboard
from bot.utils.formatters import (
    format_profile,
    format_quest_list,
    format_inventory,
)

logger = logging.getLogger(__name__)
router = Router()


# ------------------------------------------------------------------
# /start
# ------------------------------------------------------------------
@router.message(F.text.startswith("/start"))
async def cmd_start(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        user_id = user.id
        chat_id = message.chat.id
        username = user.username or user.first_name or "Anon"

        await economy_service.get_or_create_user(user_id, chat_id, username)

        # Referral check
        parts = message.text.split()
        if len(parts) > 1 and parts[1].startswith("ref_"):
            try:
                referrer_id = int(parts[1].split("_")[1])
                if referrer_id != user_id:
                    await economy_service.process_referral(user_id, referrer_id)
            except (ValueError, Exception):
                pass

        welcome = (
            f"\U0001f3ae <b>Welcome to ChatQuest, {username}!</b>\n\n"
            f"\U0001f4aa Send messages in groups to earn XP\n"
            f"\U0001f3c6 Complete quests & climb the leaderboard\n"
            f"\U0001f392 Collect items from the shop\n"
            f"\u2694\ufe0f Join guilds & battle\n\n"
            f"Use /help to see all commands."
        )
        await message.answer(welcome, reply_markup=main_menu_keyboard())
    except Exception as e:
        logger.error("Error in cmd_start: %s", e, exc_info=True)


# ------------------------------------------------------------------
# /help
# ------------------------------------------------------------------
@router.message(F.text.startswith("/help"))
async def cmd_help(message: Message) -> None:
    try:
        text = (
            "<b>\U0001f4cb ChatQuest Commands</b>\n\n"
            "\U0001f3ae <b>Core</b>\n"
            "/start \u2013 Start the bot\n"
            "/help \u2013 Show this help\n"
            "/profile \u2013 View your RPG profile\n"
            "/rank \u2013 Your rank info\n"
            "/leaderboard \u2013 XP leaderboard\n"
            "/stats \u2013 Detailed statistics\n\n"
            "\U0001f4b0 <b>Economy</b>\n"
            "/xp \u2013 XP details\n"
            "/coins \u2013 Coin balance\n"
            "/streak \u2013 Streak info\n"
            "/daily \u2013 Claim daily reward\n"
            "/shop \u2013 Open shop\n"
            "/inventory \u2013 Your items\n\n"
            "\U0001f3c6 <b>Quests & Achievements</b>\n"
            "/quests \u2013 Daily & weekly quests\n"
            "/achievements \u2013 Your achievements\n\n"
            "\u2694\ufe0f <b>Guilds & Battle</b>\n"
            "/guild \u2013 Guild info / join\n"
            "/guilds \u2013 Guild leaderboard\n"
            "/battle \u2013 Battle status\n\n"
            "\U0001f3ae <b>Minigames</b>\n"
            "/dice [bet] \u2013 Roll the dice\n"
            "/rps [rock/paper/scissors] \u2013 Rock-paper-scissors\n"
            "/trivia \u2013 Trivia quiz\n"
            "/math \u2013 Math challenge\n"
            "/guess \u2013 Guess the number\n"
            "/word \u2013 Unscramble the word\n"
            "/hangman \u2013 Hangman game\n\n"
            "\U0001f91d <b>Social</b>\n"
            "/thanks @user \u2013 Thank someone\n"
            "/tophelpers \u2013 Reputation leaderboard\n"
            "/invite \u2013 Get referral link\n"
            "/topinvites \u2013 Invite leaderboard"
        )
        await message.answer(text)
    except Exception as e:
        logger.error("Error in cmd_help: %s", e, exc_info=True)


# ------------------------------------------------------------------
# /profile
# ------------------------------------------------------------------
@router.message(F.text.startswith("/profile"))
async def cmd_profile(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        user_id = user.id
        chat_id = message.chat.id

        target_id = user_id
        # Allow /profile @mention
        if message.entities:
            for ent in message.entities:
                if ent.type == "text_mention" and ent.user:
                    target_id = ent.user.id
                    break

        profile_text = await format_profile(target_id, chat_id)
        await message.answer(profile_text, reply_markup=profile_keyboard(target_id))
    except Exception as e:
        logger.error("Error in cmd_profile: %s", e, exc_info=True)
        await message.answer("\u274c Could not load profile.")


# ------------------------------------------------------------------
# /rank
# ------------------------------------------------------------------
@router.message(F.text.startswith("/rank"))
async def cmd_rank(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        user_id = user.id
        chat_id = message.chat.id

        rank_info = await economy_service.get_rank_info(user_id, chat_id)
        await message.answer(rank_info)
    except Exception as e:
        logger.error("Error in cmd_rank: %s", e, exc_info=True)
        await message.answer("\u274c Could not load rank info.")


# ------------------------------------------------------------------
# /leaderboard
# ------------------------------------------------------------------
@router.message(F.text.startswith("/leaderboard"))
async def cmd_leaderboard(message: Message) -> None:
    try:
        chat_id = message.chat.id
        page = 0
        parts = message.text.split()
        if len(parts) > 1:
            try:
                page = int(parts[1]) - 1
                if page < 0:
                    page = 0
            except ValueError:
                pass

        lb_text, kb = await economy_service.get_leaderboard(chat_id, "xp", page)
        await message.answer(lb_text, reply_markup=kb)
    except Exception as e:
        logger.error("Error in cmd_leaderboard: %s", e, exc_info=True)
        await message.answer("\u274c Could not load leaderboard.")


# ------------------------------------------------------------------
# /xp
# ------------------------------------------------------------------
@router.message(F.text.startswith("/xp"))
async def cmd_xp(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        xp_info = await economy_service.get_xp_info(user.id, message.chat.id)
        await message.answer(xp_info)
    except Exception as e:
        logger.error("Error in cmd_xp: %s", e, exc_info=True)


# ------------------------------------------------------------------
# /coins
# ------------------------------------------------------------------
@router.message(F.text.startswith("/coins"))
async def cmd_coins(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        coins_info = await economy_service.get_coins_info(user.id, message.chat.id)
        await message.answer(coins_info)
    except Exception as e:
        logger.error("Error in cmd_coins: %s", e, exc_info=True)


# ------------------------------------------------------------------
# /streak
# ------------------------------------------------------------------
@router.message(F.text.startswith("/streak"))
async def cmd_streak(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        streak_info = await economy_service.get_streak_info(user.id, message.chat.id)
        await message.answer(streak_info)
    except Exception as e:
        logger.error("Error in cmd_streak: %s", e, exc_info=True)


# ------------------------------------------------------------------
# /quests
# ------------------------------------------------------------------
@router.message(F.text.startswith("/quests"))
async def cmd_quests(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        quest_text = await format_quest_list(user.id, message.chat.id)
        await message.answer(quest_text, reply_markup=quest_keyboard(user.id))
    except Exception as e:
        logger.error("Error in cmd_quests: %s", e, exc_info=True)
        await message.answer("\u274c Could not load quests.")


# ------------------------------------------------------------------
# /daily
# ------------------------------------------------------------------
@router.message(F.text.startswith("/daily"))
async def cmd_daily(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        daily_text = await economy_service.get_daily_info(user.id, message.chat.id)
        await message.answer(daily_text, reply_markup=daily_reward_keyboard(user.id))
    except Exception as e:
        logger.error("Error in cmd_daily: %s", e, exc_info=True)


# ------------------------------------------------------------------
# /shop
# ------------------------------------------------------------------
@router.message(F.text.startswith("/shop"))
async def cmd_shop(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        shop_text, kb = await economy_service.get_shop_page(user.id, message.chat.id)
        await message.answer(shop_text, reply_markup=kb)
    except Exception as e:
        logger.error("Error in cmd_shop: %s", e, exc_info=True)
        await message.answer("\u274c Could not open shop.")


# ------------------------------------------------------------------
# /inventory
# ------------------------------------------------------------------
@router.message(F.text.startswith("/inventory"))
async def cmd_inventory(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        inv_text = await format_inventory(user.id, message.chat.id)
        await message.answer(inv_text)
    except Exception as e:
        logger.error("Error in cmd_inventory: %s", e, exc_info=True)
        await message.answer("\u274c Could not load inventory.")


# ------------------------------------------------------------------
# /guild
# ------------------------------------------------------------------
@router.message(F.text.startswith("/guild"))
async def cmd_guild(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        guild_info = await economy_service.get_guild_info(user.id, message.chat.id)
        await message.answer(guild_info)
    except Exception as e:
        logger.error("Error in cmd_guild: %s", e, exc_info=True)
        await message.answer("\u274c Could not load guild info.")


# ------------------------------------------------------------------
# /battle
# ------------------------------------------------------------------
@router.message(F.text.startswith("/battle"))
async def cmd_battle(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        battle_info = await economy_service.get_battle_info(user.id, message.chat.id)
        await message.answer(battle_info)
    except Exception as e:
        logger.error("Error in cmd_battle: %s", e, exc_info=True)


# ------------------------------------------------------------------
# /achievements
# ------------------------------------------------------------------
@router.message(F.text.startswith("/achievements"))
async def cmd_achievements(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        ach_text = await economy_service.get_achievements(user.id, message.chat.id)
        await message.answer(ach_text)
    except Exception as e:
        logger.error("Error in cmd_achievements: %s", e, exc_info=True)


# ------------------------------------------------------------------
# /stats
# ------------------------------------------------------------------
@router.message(F.text.startswith("/stats"))
async def cmd_stats(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        stats_text = await economy_service.get_detailed_stats(user.id, message.chat.id)
        await message.answer(stats_text)
    except Exception as e:
        logger.error("Error in cmd_stats: %s", e, exc_info=True)


# ------------------------------------------------------------------
# /invite
# ------------------------------------------------------------------
@router.message(F.text.startswith("/invite"))
async def cmd_invite(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        invite_link = f"https://t.me/{settings.BOT_USERNAME}?start=ref_{user.id}"
        invite_count = await economy_service.get_invite_count(user.id)
        text = (
            f"\U0001f517 <b>Your referral link:</b>\n\n"
            f"{invite_link}\n\n"
            f"\U0001f4cb Invites: <b>{invite_count}</b>"
        )
        await message.answer(text)
    except Exception as e:
        logger.error("Error in cmd_invite: %s", e, exc_info=True)


# ------------------------------------------------------------------
# /tophelpers
# ------------------------------------------------------------------
@router.message(F.text.startswith("/tophelpers"))
async def cmd_tophelpers(message: Message) -> None:
    try:
        chat_id = message.chat.id
        page = 0
        parts = message.text.split()
        if len(parts) > 1:
            try:
                page = int(parts[1]) - 1
                if page < 0:
                    page = 0
            except ValueError:
                pass
        lb_text, kb = await economy_service.get_leaderboard(chat_id, "helpers", page)
        await message.answer(lb_text, reply_markup=kb)
    except Exception as e:
        logger.error("Error in cmd_tophelpers: %s", e, exc_info=True)


# ------------------------------------------------------------------
# /topinvites
# ------------------------------------------------------------------
@router.message(F.text.startswith("/topinvites"))
async def cmd_topinvites(message: Message) -> None:
    try:
        chat_id = message.chat.id
        page = 0
        parts = message.text.split()
        if len(parts) > 1:
            try:
                page = int(parts[1]) - 1
                if page < 0:
                    page = 0
            except ValueError:
                pass
        lb_text, kb = await economy_service.get_leaderboard(chat_id, "invites", page)
        await message.answer(lb_text, reply_markup=kb)
    except Exception as e:
        logger.error("Error in cmd_topinvites: %s", e, exc_info=True)


# ------------------------------------------------------------------
# /guilds
# ------------------------------------------------------------------
@router.message(F.text.startswith("/guilds"))
async def cmd_guilds(message: Message) -> None:
    try:
        chat_id = message.chat.id
        page = 0
        parts = message.text.split()
        if len(parts) > 1:
            try:
                page = int(parts[1]) - 1
                if page < 0:
                    page = 0
            except ValueError:
                pass
        lb_text, kb = await economy_service.get_leaderboard(chat_id, "guilds", page)
        await message.answer(lb_text, reply_markup=kb)
    except Exception as e:
        logger.error("Error in cmd_guilds: %s", e, exc_info=True)


# ------------------------------------------------------------------
# Minigames
# ------------------------------------------------------------------
@router.message(F.text.startswith("/dice"))
async def cmd_dice(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        parts = message.text.split()
        bet = int(parts[1]) if len(parts) > 1 else 0
        result = await minigames_service.dice(user.id, message.chat.id, bet)
        if isinstance(result, tuple):
            text, kb = result
            await message.answer(text, reply_markup=kb)
        else:
            await message.answer(result)
    except Exception as e:
        logger.error("Error in cmd_dice: %s", e, exc_info=True)


@router.message(F.text.startswith("/rps"))
async def cmd_rps(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        parts = message.text.split(maxsplit=1)
        choice = parts[1].strip().lower() if len(parts) > 1 else None
        result = await minigames_service.rps(user.id, message.chat.id, choice)
        if isinstance(result, tuple):
            text, kb = result
            await message.answer(text, reply_markup=kb)
        else:
            await message.answer(result)
    except Exception as e:
        logger.error("Error in cmd_rps: %s", e, exc_info=True)


@router.message(F.text.startswith("/trivia"))
async def cmd_trivia(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        result = await minigames_service.trivia(user.id, message.chat.id)
        if isinstance(result, tuple):
            text, kb = result
            await message.answer(text, reply_markup=kb)
        else:
            await message.answer(result)
    except Exception as e:
        logger.error("Error in cmd_trivia: %s", e, exc_info=True)


@router.message(F.text.startswith("/math"))
async def cmd_math(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        result = await minigames_service.math_challenge(user.id, message.chat.id)
        if isinstance(result, tuple):
            text, kb = result
            await message.answer(text, reply_markup=kb)
        else:
            await message.answer(result)
    except Exception as e:
        logger.error("Error in cmd_math: %s", e, exc_info=True)


@router.message(F.text.startswith("/guess"))
async def cmd_guess(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        result = await minigames_service.guess_number(user.id, message.chat.id)
        if isinstance(result, tuple):
            text, kb = result
            await message.answer(text, reply_markup=kb)
        else:
            await message.answer(result)
    except Exception as e:
        logger.error("Error in cmd_guess: %s", e, exc_info=True)


@router.message(F.text.startswith("/word"))
async def cmd_word(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        result = await minigames_service.word_scramble(user.id, message.chat.id)
        if isinstance(result, tuple):
            text, kb = result
            await message.answer(text, reply_markup=kb)
        else:
            await message.answer(result)
    except Exception as e:
        logger.error("Error in cmd_word: %s", e, exc_info=True)


@router.message(F.text.startswith("/hangman"))
async def cmd_hangman(message: Message) -> None:
    try:
        user = message.from_user
        if user is None:
            return
        result = await minigames_service.hangman(user.id, message.chat.id)
        if isinstance(result, tuple):
            text, kb = result
            await message.answer(text, reply_markup=kb)
        else:
            await message.answer(result)
    except Exception as e:
        logger.error("Error in cmd_hangman: %s", e, exc_info=True)
