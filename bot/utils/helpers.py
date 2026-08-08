"""General-purpose helper utilities."""

from __future__ import annotations

import base64
import math
import re
import uuid
from datetime import datetime, timezone


_BASE62_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _base62_encode(num: int) -> str:
    """Encode a positive integer into a base-62 string."""
    if num == 0:
        return _BASE62_CHARS[0]
    buf: list[str] = []
    while num:
        num, rem = divmod(num, 62)
        buf.append(_BASE62_CHARS[rem])
    return "".join(reversed(buf))


def generate_referral_code(user_id: int) -> str:
    """Generate a unique referral code: 'CQ' + base62(user_id)."""
    return "CQ" + _base62_encode(user_id)


def generate_unique_id(prefix: str = "") -> str:
    """Generate a unique ID with an optional *prefix* (UUID4 hex)."""
    return f"{prefix}{uuid.uuid4().hex}"


def format_number(n: int | float) -> str:
    """Format a number with comma-separated thousands."""
    if isinstance(n, float):
        n = int(n)
    return f"{n:,}"


def format_xp_bar(current: int, required: int, width: int = 10) -> str:
    """Return a visual XP bar like [████████░░] 71%."""
    if required <= 0:
        return "[" + "█" * width + "] 100%"
    pct = min(current / required, 1.0)
    filled = int(pct * width)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    return f"[{bar}] {int(pct * 100)}%"


def truncate_text(text: str, max_length: int = 4096) -> str:
    """Truncate *text* to *max_length*, appending '…' if needed."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "…"


def escape_markdown(text: str) -> str:
    """Escape special Markdown v2 characters."""
    special = r"_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{ch}" if ch in special else ch for ch in text)


def calculate_time_remaining(target_date: datetime) -> str:
    """Return a human-readable string for the time remaining until *target_date*."""
    now = datetime.now(timezone.utc)
    if target_date.tzinfo is None:
        target_date = target_date.replace(tzinfo=timezone.utc)
    delta = target_date - now
    if delta.total_seconds() <= 0:
        return "already ended"

    total_seconds = int(delta.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds and not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts) if parts else "<1s"
