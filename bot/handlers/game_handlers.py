from __future__ import annotations

import json
import logging
import random
import string

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from bot.cache import get_redis
from bot.services.economy_service import economy_service

logger = logging.getLogger(__name__)
router = Router()

GAME_TTL = 60  # seconds


async def _get_game_state(user_id: int, game_type: str) -> dict | None:
    """Retrieve game state from Redis."""
    redis = get_redis()
    if redis is None:
        return None
    key = f"game:{user_id}:{game_type}"
    data = await redis.get(key)
    if data is None:
        return None
    return json.loads(data)


async def _set_game_state(user_id: int, game_type: str, state: dict) -> None:
    """Store game state in Redis with TTL."""
    redis = get_redis()
    if redis is None:
        return
    key = f"game:{user_id}:{game_type}"
    await redis.set(key, json.dumps(state), ex=GAME_TTL)


async def _del_game_state(user_id: int, game_type: str) -> None:
    """Delete game state from Redis."""
    redis = get_redis()
    if redis is None:
        return
    key = f"game:{user_id}:{game_type}"
    await redis.delete(key)


# ==================================================================
# Dice  (g_dice_*)
# ==================================================================

@router.callback_query(F.data.startswith("g_dice_"))
async def cb_dice(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id if callback.message else 0
        data = callback.data

        if data == "g_dice_confirm":
            state = await _get_game_state(user_id, "dice")
            if state is None:
                await callback.message.edit_text("⏱ Dice game expired.")
                return
            bet = state.get("bet", 0)
            await _del_game_state(user_id, "dice")

            # Check balance
            balance = await economy_service.get_coins(user_id, chat_id)
            if balance < bet:
                await callback.message.edit_text("❌ Not enough coins.")
                return
            if bet > 0:
                await economy_service.remove_coins(user_id, chat_id, bet)

            roll = random.randint(1, 6)
            if roll >= 4:
                winnings = bet * 2
                await economy_service.add_coins(user_id, chat_id, winnings)
                text = (
                    f"🎲 <b>Dice Roll</b>\n\n"
                    f"You rolled: <b>{roll}</b>\n"
                    f"Bet: {bet} coins\n"
                    f"🎉 You <b>won {winnings}</b> coins!"
                )
            else:
                text = (
                    f"🎲 <b>Dice Roll</b>\n\n"
                    f"You rolled: <b>{roll}</b>\n"
                    f"Bet: {bet} coins\n"
                    f"😢 You lost. Better luck next time!"
                )
            await callback.message.edit_text(text)

        elif data == "g_dice_cancel":
            await _del_game_state(user_id, "dice")
            await callback.message.edit_text("❌ Dice game cancelled.")

    except Exception as e:
        logger.error("Error in cb_dice: %s", e, exc_info=True)


# ==================================================================
# RPS  (g_rps_*)
# ==================================================================

RPS_CHOICES = {"rock": "✊", "paper": "✋", "scissors": "✌️"}
RPS_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}


@router.callback_query(F.data.startswith("g_rps_"))
async def cb_rps(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id if callback.message else 0
        choice = callback.data.split("_", 2)[2]

        if choice not in RPS_CHOICES:
            return

        bot_choice = random.choice(list(RPS_CHOICES.keys()))
        user_emoji = RPS_CHOICES[choice]
        bot_emoji = RPS_CHOICES[bot_choice]

        if choice == bot_choice:
            result_text = "🤝 It's a <b>draw</b>!"
        elif RPS_BEATS[choice] == bot_choice:
            result_text = "🎉 You <b>won</b>!"
            await economy_service.add_coins(user_id, chat_id, 5)
        else:
            result_text = "😢 You <b>lost</b>!"

        text = (
            f"✊✋✌️ <b>Rock Paper Scissors</b>\n\n"
            f"You: {user_emoji} {choice.title()}\n"
            f"Bot: {bot_emoji} {bot_choice.title()}\n\n"
            f"{result_text}"
        )
        await callback.message.edit_text(text)

    except Exception as e:
        logger.error("Error in cb_rps: %s", e, exc_info=True)


# ==================================================================
# Trivia  (g_trivia_*)
# ==================================================================

@router.callback_query(F.data.startswith("g_trivia_"))
async def cb_trivia(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id if callback.message else 0
        answer_idx = callback.data.split("_", 2)[2]

        state = await _get_game_state(user_id, "trivia")
        if state is None:
            await callback.message.edit_text("⏱ Trivia expired.")
            return

        await _del_game_state(user_id, "trivia")
        correct = state.get("answer", "")
        question = state.get("question", "")
        reward = state.get("reward", 10)

        if answer_idx == correct:
            await economy_service.add_xp(user_id, chat_id, reward)
            text = (
                f"🧠 <b>Trivia</b>\n\n"
                f"{question}\n\n"
                f"✅ <b>Correct!</b> +{reward} XP"
            )
        else:
            text = (
                f"🧠 <b>Trivia</b>\n\n"
                f"{question}\n\n"
                f"❌ Wrong! The answer was: <b>{correct}</b>"
            )
        await callback.message.edit_text(text)

    except Exception as e:
        logger.error("Error in cb_trivia: %s", e, exc_info=True)


# ==================================================================
# Math  (g_math_*)
# ==================================================================

@router.callback_query(F.data.startswith("g_math_"))
async def cb_math(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id if callback.message else 0
        answer = callback.data.split("_", 2)[2]

        state = await _get_game_state(user_id, "math")
        if state is None:
            await callback.message.edit_text("⏱ Math challenge expired.")
            return

        await _del_game_state(user_id, "math")
        correct_answer = str(state.get("answer", ""))
        problem = state.get("problem", "")
        reward = state.get("reward", 10)

        if answer == correct_answer:
            await economy_service.add_xp(user_id, chat_id, reward)
            text = (
                f"🔢 <b>Math Challenge</b>\n\n"
                f"{problem}\n\n"
                f"✅ <b>Correct!</b> +{reward} XP"
            )
        else:
            text = (
                f"🔢 <b>Math Challenge</b>\n\n"
                f"{problem}\n\n"
                f"❌ Wrong! The answer was: <b>{correct_answer}</b>"
            )
        await callback.message.edit_text(text)

    except Exception as e:
        logger.error("Error in cb_math: %s", e, exc_info=True)


# ==================================================================
# Guess the Number  (g_guess_*)
# ==================================================================

@router.callback_query(F.data.startswith("g_guess_"))
async def cb_guess(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id if callback.message else 0
        data = callback.data

        # g_guess_num_{number}  or  g_guess_start
        parts = data.split("_")

        if data == "g_guess_start":
            target = random.randint(1, 100)
            await _set_game_state(user_id, "guess", {"target": target, "attempts": 0, "max_attempts": 7})
            text = (
                f"🔢 <b>Guess the Number</b>\n\n"
                f"I'm thinking of a number between <b>1</b> and <b>100</b>.\n"
                f"You have <b>7</b> attempts.\n\n"
                f"Send your guess as a number."
            )
            await callback.message.edit_text(text)
            return

        # This handles text-message guesses via a text handler or callback
        # For callback-based guessing we expect g_guess_num_{n}
        if len(parts) >= 4 and parts[2] == "num":
            try:
                guess_num = int(parts[3])
            except ValueError:
                return

            state = await _get_game_state(user_id, "guess")
            if state is None:
                await callback.message.edit_text("⏱ Guess game expired. Start a new one!")
                return

            target = state["target"]
            attempts = state["attempts"] + 1
            max_attempts = state["max_attempts"]
            diff = abs(guess_num - target)

            if guess_num == target:
                await _del_game_state(user_id, "guess")
                reward = max(5, 30 - (attempts - 1) * 4)
                await economy_service.add_xp(user_id, chat_id, reward)
                text = f"🎉 <b>Correct!</b> The number was {target}.\nYou got it in {attempts} attempts! +{reward} XP"
                await callback.message.edit_text(text)
            elif attempts >= max_attempts:
                await _del_game_state(user_id, "guess")
                text = f"😢 <b>Game Over!</b> The number was <b>{target}</b>.\nBetter luck next time!"
                await callback.message.edit_text(text)
            else:
                # Hot/cold hints
                if diff <= 5:
                    hint = "🔥 Very hot!"
                elif diff <= 15:
                    hint = "🟡 Warm"
                elif diff <= 30:
                    hint = "🟦 Cool"
                else:
                    hint = "🧊 Cold!"

                direction = "⬆️ Higher" if guess_num < target else "⬇️ Lower"
                remaining = max_attempts - attempts

                await _set_game_state(user_id, "guess", {**state, "attempts": attempts})

                # Build a quick-pick keyboard for nearby numbers
                buttons = []
                row = []
                for n in range(max(1, guess_num - 5), min(101, guess_num + 6)):
                    row.append(InlineKeyboardButton(text=str(n), callback_data=f"g_guess_num_{n}"))
                    if len(row) == 5:
                        buttons.append(row)
                        row = []
                if row:
                    buttons.append(row)
                kb = InlineKeyboardMarkup(inline_keyboard=buttons)

                text = (
                    f"🔢 <b>Guess the Number</b>\n\n"
                    f"Your guess: <b>{guess_num}</b>\n"
                    f"{hint} {direction}\n"
                    f"Attempts left: <b>{remaining}</b>"
                )
                await callback.message.edit_text(text, reply_markup=kb)

    except Exception as e:
        logger.error("Error in cb_guess: %s", e, exc_info=True)


# ==================================================================
# Word Scramble  (g_word_*)
# ==================================================================

@router.callback_query(F.data.startswith("g_word_"))
async def cb_word(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id if callback.message else 0
        answer = callback.data.split("_", 2)[2]

        state = await _get_game_state(user_id, "word")
        if state is None:
            await callback.message.edit_text("⏱ Word game expired.")
            return

        await _del_game_state(user_id, "word")
        correct = state.get("word", "").lower()
        scrambled = state.get("scrambled", "")
        reward = state.get("reward", 15)

        if answer.lower() == correct:
            await economy_service.add_xp(user_id, chat_id, reward)
            text = (
                f"📝 <b>Word Scramble</b>\n\n"
                f"Scrambled: <b>{scrambled}</b>\n"
                f"Your answer: <b>{answer}</b>\n\n"
                f"✅ <b>Correct!</b> +{reward} XP"
            )
        else:
            text = (
                f"📝 <b>Word Scramble</b>\n\n"
                f"Scrambled: <b>{scrambled}</b>\n"
                f"Your answer: <b>{answer}</b>\n\n"
                f"❌ Wrong! The word was: <b>{correct}</b>"
            )
        await callback.message.edit_text(text)

    except Exception as e:
        logger.error("Error in cb_word: %s", e, exc_info=True)


# ==================================================================
# Hangman  (g_hang_*)
# ==================================================================

HANGMAN_STAGES = [
    """
  +---+
  |   |
      |
      |
      |
      |
=========""",
    """
  +---+
  |   |
  O   |
      |
      |
      |
=========""",
    """
  +---+
  |   |
  O   |
  |   |
      |
      |
=========""",
    """
  +---+
  |   |
  O   |
 /|   |
      |
      |
=========""",
    """
  +---+
  |   |
  O   |
 /|\\  |
      |
      |
=========""",
    """
  +---+
  |   |
  O   |
 /|\\  |
 /    |
      |
=========""",
    """
  +---+
  |   |
  O   |
 /|\\  |
 / \\  |
      |
=========""",
]


@router.callback_query(F.data.startswith("g_hang_"))
async def cb_hangman(callback: CallbackQuery) -> None:
    try:
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id if callback.message else 0
        data = callback.data

        # g_hang_letter_{letter}
        parts = data.split("_")
        if len(parts) < 3:
            await callback.answer()
            return

        letter = parts[2].upper()
        if len(letter) != 1 or letter not in string.ascii_uppercase:
            await callback.answer("Invalid letter.", show_alert=True)
            return

        state = await _get_game_state(user_id, "hangman")
        if state is None:
            await callback.answer("Game expired.", show_alert=True)
            return

        word = state["word"]
        guessed = set(state.get("guessed", []))
        wrong = state.get("wrong", 0)

        if letter in guessed:
            await callback.answer("Already guessed!", show_alert=True)
            return

        guessed.add(letter)

        if letter in word:
            # Correct guess
            pass
        else:
            wrong += 1

        # Check win
        word_set = set(word.upper())
        guessed_inter = word_set & guessed
        won = guessed_inter == word_set
        lost = wrong >= len(HANGMAN_STAGES) - 1

        if won or lost:
            await _del_game_state(user_id, "hangman")
            if won:
                reward = 20
                await economy_service.add_xp(user_id, chat_id, reward)
                status = f"🎉 <b>You won!</b> The word was: <b>{word}</b>\n+{reward} XP"
            else:
                status = f"😢 <b>Game Over!</b> The word was: <b>{word}</b>"
            text = f"🎯 <b>Hangman</b>\n\n{HANGMAN_STAGES[wrong]}\n{status}"
            await callback.message.edit_text(text)
            await callback.answer()
            return

        # Build display
        display = " ".join(c.upper() if c.upper() in guessed else "_" for c in word)
        guessed_letters = ", ".join(sorted(guessed))

        await _set_game_state(user_id, "hangman", {**state, "guessed": list(guessed), "wrong": wrong})

        # Build A-Z keyboard, hiding already guessed
        buttons = []
        row = []
        for c in string.ascii_uppercase:
            if c in guessed:
                row.append(InlineKeyboardButton(text="✅", callback_data=f"g_hang_none"))
            else:
                row.append(InlineKeyboardButton(text=c, callback_data=f"g_hang_letter_{c}"))
            if len(row) == 7:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

        text = (
            f"🎯 <b>Hangman</b>\n\n"
            f"<pre>{HANGMAN_STAGES[wrong]}</pre>\n"
            f"Word: <code>{display}</code>\n"
            f"Letters: {guessed_letters}\n"
            f"Wrong: {wrong}/{len(HANGMAN_STAGES) - 1}"
        )
        await callback.message.edit_text(text, reply_markup=kb)
        await callback.answer()

    except Exception as e:
        logger.error("Error in cb_hangman: %s", e, exc_info=True)
