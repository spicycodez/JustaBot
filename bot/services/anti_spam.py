from __future__ import annotations

import re
from bot.cache import get_cache, set_cache, get_hash, set_hash, delete_cache
from bot.config import settings
from bot.models import User


# Config shortcuts
ANTI_SPAM_THRESHOLD = settings.ANTI_SPAM_THRESHOLD          # 3
FREEZE_1 = settings.ANTI_SPAM_FREEZE_1                      # 300  (5 min)
FREEZE_2 = settings.ANTI_SPAM_FREEZE_2                      # 600  (10 min)
FREEZE_3 = settings.ANTI_SPAM_FREEZE_3                      # 1800 (30 min)
XP_COOLDOWN = settings.XP_COOLDOWN                          # 20s

# Patterns
_EMOJI_ONLY_RE = re.compile(r"^[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF\s]+$")
_LINK_RE = re.compile(r"https?://\S+", re.IGNORECASE)


def _freeze_duration(spam_count: int) -> int:
    """Escalating freeze based on how many times the threshold was hit."""
    hits = spam_count // ANTI_SPAM_THRESHOLD
    if hits >= 3:
        return FREEZE_3
    if hits == 2:
        return FREEZE_2
    if hits == 1:
        return FREEZE_1
    return 0


async def _is_within_cooldown(user_id: int, chat_id: int) -> bool:
    """Check if the user is still within the XP cooldown window."""
    key = f"cooldown:{user_id}:{chat_id}"
    return (await get_cache(key)) is not None


async def _is_copy_paste(user_id: int, chat_id: int, message_text: str) -> bool:
    """Detect if the same message was sent by multiple users recently (copy-paste)."""
    key = f"msg_fingerprint:{chat_id}"
    fingerprint = message_text.strip()[:200]  # normalise / truncate
    if len(fingerprint) < 15:
        return False
    senders = await get_hash(key, fingerprint)
    if senders is None:
        await set_hash(key, fingerprint, str(user_id))
        return False
    sender_list = senders.split(",") if isinstance(senders, str) else []
    if str(user_id) not in sender_list:
        if len(sender_list) >= 3:
            return True
        await set_hash(key, fingerprint, f"{senders},{user_id}")
    return False


async def check_spam(user_id: int, chat_id: int, message_text: str) -> dict:
    """Run all spam checks against the message.

    Returns dict with keys: is_spam, freeze_duration, spam_count.

    Rules (any triggers a spam hit):
      1. Same text as the user's last message
      2. Emoji-only message
      3. Sent within XP cooldown (rate limit)
      4. Link-only message
      5. Sticker message  (message_text == "__sticker__")
      6. Forwarded message  (message_text == "__forward__")
      7. Copy-paste detected across multiple users

    Escalation: threshold×1 → 5 min, ×2 → 10 min, ×3 → 30 min freeze.
    """
    spam_count_key = f"spam_count:{user_id}:{chat_id}"
    raw = await get_cache(spam_count_key)
    current_count = int(raw) if raw is not None else 0

    is_spam = False

    # Rule 1 – same as last message
    last_text_key = f"last_msg:{user_id}:{chat_id}"
    last_text = await get_cache(last_text_key)
    if last_text is not None and message_text == last_text:
        is_spam = True

    # Rule 2 – emoji only
    if not is_spam and _EMOJI_ONLY_RE.match(message_text.strip()):
        is_spam = True

    # Rule 3 – within cooldown
    if not is_spam and await _is_within_cooldown(user_id, chat_id):
        is_spam = True

    # Rule 4 – link only
    if not is_spam and _LINK_RE.match(message_text.strip()) and len(message_text.strip()) < 100:
        is_spam = True

    # Rule 5 – sticker
    if message_text == "__sticker__":
        is_spam = True

    # Rule 6 – forwarded
    if message_text == "__forward__":
        is_spam = True

    # Rule 7 – copy-paste across users
    if not is_spam and await _is_copy_paste(user_id, chat_id, message_text):
        is_spam = True

    # Update tracking
    await set_cache(last_text_key, message_text)

    if is_spam:
        current_count += 1
        await set_cache(spam_count_key, str(current_count))
        freeze = _freeze_duration(current_count)
    else:
        freeze = 0

    return {
        "is_spam": is_spam,
        "freeze_duration": freeze,
        "spam_count": current_count,
    }


async def reset_spam_count(user_id: int, chat_id: int) -> None:
    """Reset the spam counter for a user in a chat."""
    key = f"spam_count:{user_id}:{chat_id}"
    await delete_cache(key)


async def is_user_frozen(user_id: int) -> bool:
    """Check whether a user currently has an active XP freeze."""
    from datetime import datetime, timezone
    try:
        user = await User.find_one(User.telegram_id == user_id)
        if user and user.xp_frozen_until and user.xp_frozen_until > datetime.now(timezone.utc):
            return True
    except Exception:
        pass
    return False
