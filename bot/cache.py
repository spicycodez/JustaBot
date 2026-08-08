"""Redis async helpers using redis.asyncio."""

from __future__ import annotations

from typing import Dict, Optional

import redis.asyncio as redis

from bot.config import settings

redis_client: Optional[redis.Redis] = None


async def init_redis() -> redis.Redis:
    """Create the global redis client and store it in the module variable."""
    global redis_client
    redis_client = redis.Redis(
        url=settings.REDIS_URL,
        password=settings.REDIS_PASSWORD or None,
        decode_responses=True,
    )
    return redis_client


async def get_cache(key: str) -> Optional[str]:
    """Return the cached value for *key*, or ``None`` on miss."""
    if redis_client is None:
        return None
    return await redis_client.get(key)


async def set_cache(key: str, value: str, expire: Optional[int] = None) -> None:
    """Set *key* to *value*.  Optionally provide *expire* in seconds."""
    if redis_client is None:
        return
    if expire:
        await redis_client.setex(key, expire, value)
    else:
        await redis_client.set(key, value)


async def delete_cache(key: str) -> None:
    """Remove *key* from Redis."""
    if redis_client is None:
        return
    await redis_client.delete(key)


async def increment_cache(key: str) -> int:
    """Atomically increment *key* and return the new value."""
    if redis_client is None:
        return 0
    return await redis_client.incr(key)


async def get_hash(key: str, field: str) -> Optional[str]:
    """Return a single field from a Redis hash."""
    if redis_client is None:
        return None
    return await redis_client.hget(key, field)


async def set_hash(key: str, field: str, value: str) -> None:
    """Set a single field in a Redis hash."""
    if redis_client is None:
        return
    await redis_client.hset(key, field, value)


async def get_all_hash(key: str) -> Dict[str, str]:
    """Return all fields and values of a Redis hash."""
    if redis_client is None:
        return {}
    return await redis_client.hgetall(key)
