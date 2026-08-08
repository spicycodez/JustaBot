import json
import random
import math
import logging
import os
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from bot.models.user import User

logger = logging.getLogger(__name__)

_MINIGAMES_DATA: Optional[Dict[str, Any]] = None

# Redis key prefix
_REDIS_PREFIX = "chatquest:minigame"
_COOLDOWN_SECONDS = 30

# Hangman stages
HANGMAN_STAGES = [
    "```
  +---+
  |   |
      |
      |
      |
      |
=========""",
    "```
  +---+
  |   |
  O   |
      |
      |
      |
=========""",
    "```
  +---+
  |   |
  O   |
  |   |
      |
      |
=========""",
    "```
  +---+
  |   |
  O   |
 /|   |
      |
      |
=========""",
    "```
  +---+
  |   |
  O   |
 /|\\  |
      |
      |
=========""",
    "```
  +---+
  |   |
  O   |
 /|\\  |
 /    |
      |
=========""",
    "```
  +---+
  |   |
  O   |
 /|\\  |
 / \\  |
      |
=========""",
]


def _load_minigames() -> Dict[str, Any]:
    """Load minigames data from data/minigames.json."""
    global _MINIGAMES_DATA
    if _MINIGAMES_DATA is None:
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "minigames.json",
        )
        with open(data_path, "r", encoding="utf-8") as f:
            _MINIGAMES_DATA = json.load(f)
    return _MINIGAMES_DATA


def _get_redis_client():
    """Get Redis client. Returns None if not available."""
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


def check_minigame_cooldown(user_id: int, game_type: str) -> bool:
    """
    Check if user is on cooldown for a minigame (30s Redis TTL).
    Returns True if on cooldown, False if can play.
    """
    redis_client = _get_redis_client()
    if not redis_client:
        return False

    key = f"{_REDIS_PREFIX}:cooldown:{user_id}:{game_type}"
    return redis_client.exists(key) == 1


def _set_cooldown(user_id: int, game_type: str) -> None:
    """Set cooldown for a minigame."""
    redis_client = _get_redis_client()
    if redis_client:
        key = f"{_REDIS_PREFIX}:cooldown:{user_id}:{game_type}"
        redis_client.setex(key, _COOLDOWN_SECONDS, "1")


def award_minigame_xp(db: Session, user_id: int, won: bool) -> int:
    """
    Award XP for playing a minigame. 10 XP for playing, +20 for winning.
    Returns total XP awarded.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return 0

    xp = 10  # play bonus
    if won:
        xp += 20  # win bonus

    user.total_xp += xp
    user.season_xp += xp
    db.commit()

    return xp


def _ensure_user(db: Session, user_id: int) -> User:
    """Get or create a user."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        user = User(user_id=user_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def play_dice(db: Session, user_id: int, bet: int, guess: int = None) -> Dict[str, Any]:
    """
    Play dice game. Roll 1-6, if guess matches: 2x bet (coins).
    Returns game result with roll, guess, and winnings.
    """
    if check_minigame_cooldown(user_id, "dice"):
        raise ValueError("You're on cooldown. Wait 30 seconds.")

    user = _ensure_user(db, user_id)

    if bet < 0:
        raise ValueError("Bet must be positive.")
    if user.coins < bet:
        raise ValueError(f"Not enough coins. You have {user.coins}.")

    if guess is not None and (guess < 1 or guess > 6):
        raise ValueError("Guess must be between 1 and 6.")

    roll = random.randint(1, 6)
    won = (guess is not None and roll == guess)

    if won:
        winnings = bet * 2
        user.coins += winnings - bet  # net gain = bet
    else:
        winnings = 0
        user.coins -= bet

    _set_cooldown(user_id, "dice")
    xp = award_minigame_xp(db, user_id, won)
    db.refresh(user)

    return {
        "game": "dice",
        "roll": roll,
        "guess": guess,
        "won": won,
        "bet": bet,
        "winnings": winnings,
        "net_coins": winnings - bet,
        "xp_awarded": xp,
        "balance": user.coins,
    }


def play_rps(db: Session, user_id: int, choice: str) -> Dict[str, Any]:
    """
    Play Rock-Paper-Scissors against the bot.
    choice: 'rock', 'paper', or 'scissors'
    Returns game result.
    """
    if check_minigame_cooldown(user_id, "rps"):
        raise ValueError("You're on cooldown. Wait 30 seconds.")

    choice = choice.lower().strip()
    valid = ["rock", "paper", "scissors"]
    if choice not in valid:
        raise ValueError(f"Invalid choice. Pick from: {', '.join(valid)}")

    bot_choice = random.choice(valid)

    # Determine winner
    if choice == bot_choice:
        result = "draw"
    elif (
        (choice == "rock" and bot_choice == "scissors")
        or (choice == "paper" and bot_choice == "rock")
        or (choice == "scissors" and bot_choice == "paper")
    ):
        result = "win"
    else:
        result = "lose"

    _set_cooldown(user_id, "rps")
    xp = award_minigame_xp(db, user_id, result == "win")

    return {
        "game": "rps",
        "your_choice": choice,
        "bot_choice": bot_choice,
        "result": result,
        "xp_awarded": xp,
    }


def play_trivia(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Play trivia. Random question from data/minigames.json.
    Stores the correct answer index in Redis for verification.
    Returns the question and options.
    """
    if check_minigame_cooldown(user_id, "trivia"):
        raise ValueError("You're on cooldown. Wait 30 seconds.")

    data = _load_minigames()
    question_data = random.choice(data["trivia_questions"])

    # Store answer in Redis
    redis_client = _get_redis_client()
    key = f"{_REDIS_PREFIX}:trivia:{user_id}"
    if redis_client:
        redis_client.setex(key, 120, str(question_data["answer"]))  # 2 min to answer

    _set_cooldown(user_id, "trivia")

    return {
        "game": "trivia",
        "question": question_data["question"],
        "options": question_data["options"],
        "options_count": len(question_data["options"]),
    }


def play_math(db: Session, user_id: int, difficulty: str = "easy") -> Dict[str, Any]:
    """
    Play math challenge. Generates a problem and stores the answer in Redis.
    difficulty: 'easy', 'medium', 'hard'
    Returns the math problem and difficulty.
    """
    if check_minigame_cooldown(user_id, "math"):
        raise ValueError("You're on cooldown. Wait 30 seconds.")

    if difficulty not in ("easy", "medium", "hard"):
        difficulty = "easy"

    data = _load_minigames()
    config = data["math_difficulties"][difficulty]
    low, high = config["range"]
    ops = config["ops"]

    op = random.choice(ops)
    a = random.randint(low, high)
    b = random.randint(low, high)

    if op == "+":
        answer = a + b
        problem = f"{a} + {b} = ?"
    elif op == "-":
        if a < b:
            a, b = b, a
        answer = a - b
        problem = f"{a} - {b} = ?"
    elif op == "*":
        # Use smaller numbers for multiplication
        a = random.randint(2, min(20, high))
        b = random.randint(2, min(20, high))
        answer = a * b
        problem = f"{a} × {b} = ?"
    elif op == "/":
        # Generate clean division
        b = random.randint(2, min(20, high))
        answer = random.randint(1, min(20, high))
        a = b * answer
        problem = f"{a} ÷ {b} = ?"
    else:
        answer = a + b
        problem = f"{a} + {b} = ?"

    # Store answer in Redis
    redis_client = _get_redis_client()
    key = f"{_REDIS_PREFIX}:math:{user_id}"
    if redis_client:
        redis_client.setex(key, 120, str(answer))  # 2 min to answer

    _set_cooldown(user_id, "math")

    return {
        "game": "math",
        "difficulty": difficulty,
        "problem": problem,
    }


def play_guess(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Play number guessing game. Guess a number between 1-100.
    7 attempts allowed, with hot/cold hints.
    Stores state in Redis.
    Returns initial game state.
    """
    if check_minigame_cooldown(user_id, "guess"):
        raise ValueError("You're on cooldown. Wait 30 seconds.")

    target = random.randint(1, 100)
    max_attempts = 7

    # Store state in Redis
    redis_client = _get_redis_client()
    key = f"{_REDIS_PREFIX}:guess:{user_id}"
    if redis_client:
        state = {
            "target": target,
            "attempts": 0,
            "max_attempts": max_attempts,
            "guesses": [],
        }
        redis_client.setex(key, 600, json.dumps(state))  # 10 min to play

    _set_cooldown(user_id, "guess")

    return {
        "game": "guess",
        "range": [1, 100],
        "max_attempts": max_attempts,
        "message": "I'm thinking of a number between 1 and 100. You have 7 attempts!",
    }


def check_guess(db: Session, user_id: int, guess: int) -> Dict[str, Any]:
    """
    Check a guess in the number guessing game.
    Returns hint (hot/cold) and remaining attempts.
    """
    if guess < 1 or guess > 100:
        raise ValueError("Guess must be between 1 and 100.")

    redis_client = _get_redis_client()
    key = f"{_REDIS_PREFIX}:guess:{user_id}"
    if not redis_client or not redis_client.exists(key):
        raise ValueError("No active guessing game. Start a new one!")

    state = json.loads(redis_client.get(key))
    target = state["target"]
    attempts = state["attempts"]
    max_attempts = state["max_attempts"]
    guesses = state["guesses"]

    if guess in guesses:
        return {"message": "You already guessed that number!", "attempts_left": max_attempts - attempts}

    attempts += 1
    guesses.append(guess)

    if guess == target:
        won = True
        message = f"🎉 Correct! The number was {target}. You got it in {attempts} attempts!"
        redis_client.delete(key)
        xp = award_minigame_xp(db, user_id, True)
        return {"won": True, "message": message, "attempts": attempts, "xp_awarded": xp}

    # Calculate distance for hot/cold
    distance = abs(guess - target)
    previous_distance = None
    if len(guesses) >= 2:
        previous_distance = abs(guesses[-2] - target)

    if distance <= 5:
        hint = "🔥 Very hot!"
    elif distance <= 15:
        hint = "🌡️ Hot!"
    elif distance <= 30:
        hint = "😐 Warm"
    elif distance <= 50:
        hint = "❄️ Cold"
    else:
        hint = "🥶 Very cold!"

    # Direction hint
    if guess < target:
        direction = "⬆️ Higher"
    else:
        direction = "⬇️ Lower"

    # Warmer/colder compared to last guess
    if previous_distance is not None:
        if distance < previous_distance:
            hint += " (getting warmer!)"
        elif distance > previous_distance:
            hint += " (getting colder!)"

    if attempts >= max_attempts:
        redis_client.delete(key)
        xp = award_minigame_xp(db, user_id, False)
        return {
            "won": False,
            "message": f"😞 Game over! The number was {target}.",
            "attempts": attempts,
            "xp_awarded": xp,
        }

    # Save state
    state["attempts"] = attempts
    state["guesses"] = guesses
    redis_client.setex(key, 600, json.dumps(state))

    return {
        "won": False,
        "hint": f"{hint} {direction}",
        "attempts_left": max_attempts - attempts,
        "attempts_used": attempts,
    }


def play_word(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Play word scramble game. Scrambles a random word.
    Stores the original word in Redis for verification.
    Returns the scrambled word.
    """
    if check_minigame_cooldown(user_id, "word"):
        raise ValueError("You're on cooldown. Wait 30 seconds.")

    data = _load_minigames()
    word = random.choice(data["words"])

    # Scramble
    letters = list(word.upper())
    scrambled = letters
    attempts = 0
    while scrambled == letters and attempts < 100:
        random.shuffle(scrambled)
        attempts += 1
    scrambled_word = "".join(scrambled)

    # Store in Redis
    redis_client = _get_redis_client()
    key = f"{_REDIS_PREFIX}:word:{user_id}"
    if redis_client:
        redis_client.setex(key, 120, word.lower())  # 2 min to answer

    _set_cooldown(user_id, "word")

    return {
        "game": "word_scramble",
        "scrambled": scrambled_word,
        "length": len(word),
        "hint": word[0].upper() + "_" * (len(word) - 2) + word[-1].upper() if len(word) > 2 else None,
    }


def play_hangman(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Play hangman. Picks a random word, 6 wrong guesses allowed.
    Stores state in Redis.
    Returns initial game state with the word display and hangman art.
    """
    if check_minigame_cooldown(user_id, "hangman"):
        raise ValueError("You're on cooldown. Wait 30 seconds.")

    data = _load_minigames()
    word = random.choice(data["words"]).upper()

    state = {
        "word": word,
        "guessed": [],
        "wrong_guesses": 0,
        "max_wrong": 6,
    }

    # Store in Redis
    redis_client = _get_redis_client()
    key = f"{_REDIS_PREFIX}:hangman:{user_id}"
    if redis_client:
        redis_client.setex(key, 600, json.dumps(state))  # 10 min

    _set_cooldown(user_id, "hangman")

    display = _format_hangman_display(state)
    return {
        "game": "hangman",
        "display": display["word_display"],
        "art": display["art"],
        "wrong_guesses": 0,
        "max_wrong": 6,
        "guessed": [],
    }


def check_hangman_letter(db: Session, user_id: int, letter: str) -> Dict[str, Any]:
    """
    Guess a letter in hangman.
    Returns updated display, art, and game status.
    """
    letter = letter.upper().strip()
    if len(letter) != 1 or not letter.isalpha():
        raise ValueError("Guess a single letter.")

    redis_client = _get_redis_client()
    key = f"{_REDIS_PREFIX}:hangman:{user_id}"
    if not redis_client or not redis_client.exists(key):
        raise ValueError("No active hangman game. Start a new one!")

    state = json.loads(redis_client.get(key))
    word = state["word"]
    guessed = state["guessed"]
    wrong_guesses = state["wrong_guesses"]
    max_wrong = state["max_wrong"]

    if letter in guessed:
        return {
            "message": f"You already guessed '{letter}'!",
            **_format_hangman_display(state),
        }

    guessed.append(letter)

    if letter in word:
        # Correct guess
        message = f"✅ '{letter}' is in the word!"
    else:
        # Wrong guess
        wrong_guesses += 1
        message = f"❌ '{letter}' is not in the word."

    state["guessed"] = guessed
    state["wrong_guesses"] = wrong_guesses

    # Check win/loss
    word_guessed = all(c in guessed for c in word)
    if word_guessed:
        redis_client.delete(key)
        xp = award_minigame_xp(db, user_id, True)
        return {
            "won": True,
            "message": f"🎉 You got it! The word was '{word}'!",
            "word": word,
            "xp_awarded": xp,
        }

    if wrong_guesses >= max_wrong:
        redis_client.delete(key)
        xp = award_minigame_xp(db, user_id, False)
        return {
            "won": False,
            "message": f"💀 Game over! The word was '{word}'.",
            "word": word,
            "xp_awarded": xp,
        }

    # Save state
    redis_client.setex(key, 600, json.dumps(state))

    display = _format_hangman_display(state)
    return {
        "won": False,
        "message": message,
        **display,
        "wrong_guesses": wrong_guesses,
        "max_wrong": max_wrong,
    }


def _format_hangman_display(state: Dict[str, Any]) -> Dict[str, str]:
    """Format the hangman word display and ASCII art."""
    word = state["word"]
    guessed = state["guessed"]
    wrong = state["wrong_guesses"]

    word_display = " ".join(c if c in guessed else "_" for c in word)
    art = HANGMAN_STAGES[min(wrong, len(HANGMAN_STAGES) - 1)]

    return {
        "word_display": word_display,
        "art": art,
    }


def verify_trivia_answer(db: Session, user_id: int, answer_index: int) -> Dict[str, Any]:
    """
    Verify a trivia answer. Awards XP if correct.
    Returns result.
    """
    redis_client = _get_redis_client()
    key = f"{_REDIS_PREFIX}:trivia:{user_id}"
    if not redis_client or not redis_client.exists(key):
        raise ValueError("No active trivia question. Start a new one!")

    correct = int(redis_client.get(key))
    redis_client.delete(key)

    won = answer_index == correct
    xp = award_minigame_xp(db, user_id, won)

    return {
        "game": "trivia",
        "your_answer": answer_index,
        "correct_answer": correct,
        "won": won,
        "xp_awarded": xp,
    }


def verify_math_answer(db: Session, user_id: int, answer: int) -> Dict[str, Any]:
    """
    Verify a math answer. Awards XP if correct.
    Returns result.
    """
    redis_client = _get_redis_client()
    key = f"{_REDIS_PREFIX}:math:{user_id}"
    if not redis_client or not redis_client.exists(key):
        raise ValueError("No active math challenge. Start a new one!")

    correct = int(redis_client.get(key))
    redis_client.delete(key)

    won = answer == correct
    xp = award_minigame_xp(db, user_id, won)

    return {
        "game": "math",
        "your_answer": answer,
        "correct_answer": correct,
        "won": won,
        "xp_awarded": xp,
    }


def verify_word_answer(db: Session, user_id: int, answer: str) -> Dict[str, Any]:
    """
    Verify a word scramble answer. Awards XP if correct.
    Returns result.
    """
    redis_client = _get_redis_client()
    key = f"{_REDIS_PREFIX}:word:{user_id}"
    if not redis_client or not redis_client.exists(key):
        raise ValueError("No active word scramble. Start a new one!")

    correct = redis_client.get(key)
    redis_client.delete(key)

    won = answer.lower().strip() == correct.lower().strip()
    xp = award_minigame_xp(db, user_id, won)

    return {
        "game": "word_scramble",
        "your_answer": answer,
        "correct_answer": correct,
        "won": won,
        "xp_awarded": xp,
    }
