"""
Redis async client — singleton pattern.
Uses redis-py asyncio interface with connection pooling.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.core.config import settings

# ── Singleton client ───────────────────────────────────────────────────────────
_redis_client: Redis | None = None


async def get_redis_client() -> Redis:
    """Return (and lazily initialize) the shared Redis connection pool."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection pool — call on app shutdown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


# ── FastAPI dependency ─────────────────────────────────────────────────────────
async def get_redis() -> AsyncGenerator[Redis, None]:
    """Yield the Redis client as a FastAPI injectable dependency."""
    client = await get_redis_client()
    yield client


# ── Session helpers ────────────────────────────────────────────────────────────
async def set_session(redis: Redis, key: str, value: str) -> None:
    """Store a session value with the configured TTL."""
    await redis.set(key, value, ex=settings.redis_session_ttl)


async def get_session_value(redis: Redis, key: str) -> str | None:
    """Retrieve a session value, returning None if not found."""
    return await redis.get(key)


async def delete_session(redis: Redis, key: str) -> None:
    """Remove a session key from Redis."""
    await redis.delete(key)
