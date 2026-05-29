"""
Core Session & Memory Management
Handles short-term AI chat history and conversation state using Redis.
"""
from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

from app.core.config import settings
from app.core.redis_client import get_redis_client


class ChatSessionManager:
    """
    Manages short-term conversation memory and basic state in Redis.
    Uses Lists (RPUSH/LRANGE) for fast message append/read operations.
    """

    def __init__(self, redis: Redis | None = None):
        # We allow injecting a redis client, but default to the app singleton
        self.redis: Redis | None = redis

    async def _get_redis(self) -> Redis:
        if self.redis is None:
            self.redis = await get_redis_client()
        return self.redis

    def _get_history_key(self, phone: str) -> str:
        """The redis key for storing the raw chat message history."""
        return f"chat:history:{phone}"

    def _get_state_key(self, phone: str) -> str:
        """The redis key for storing transient state (e.g. active cart, context)."""
        return f"chat:state:{phone}"

    def _get_cart_key(self, phone: str) -> str:
        """Dedicated Redis key for the shopping cart, separate from state to allow atomic clears."""
        return f"cart:{phone}"

    async def get_chat_history(self, phone: str, limit: int = 50) -> list[dict[str, Any]]:
        """
        Retrieves the last N messages from the conversation.
        Returns them as a list of dictionaries (role, text).
        """
        redis = await self._get_redis()
        key = self._get_history_key(phone)
        
        # Get the most recent `limit` items. Redis LRANGE is 0-indexed.
        # To get the LAST N items, we use negative indices: -limit to -1.
        raw_messages = await redis.lrange(key, -limit, -1)
        
        history: list[dict[str, Any]] = []
        for raw in raw_messages:
            try:
                msg = json.loads(raw)
                history.append(msg)
            except json.JSONDecodeError:
                continue
                
        return history

    async def add_message(self, phone: str, role: str, content: str) -> None:
        """
        Appends a new message to the conversation history.
        `role` should typically be "user" or "model" (Gemini conventions).
        """
        redis = await self._get_redis()
        key = self._get_history_key(phone)
        
        msg_payload = json.dumps({"role": role, "content": content})
        
        # Pipeline: Push message, keep only last 100, reset TTL
        async with redis.pipeline(transaction=False) as pipe:
            pipe.rpush(key, msg_payload)
            pipe.ltrim(key, -100, -1)  # Keep only the last 100 messages to avoid bloat
            pipe.expire(key, settings.redis_session_ttl)
            await pipe.execute()

    async def get_state(self, phone: str) -> dict[str, Any]:
        """Retrieves the transient JSON state for this conversation."""
        redis = await self._get_redis()
        key = self._get_state_key(phone)
        
        raw_state = await redis.get(key)
        if not raw_state:
            return {}
            
        try:
            return dict(json.loads(raw_state))
        except json.JSONDecodeError:
            return {}

    async def update_state(self, phone: str, new_data: dict[str, Any]) -> None:
        """Merges new_data into the existing transient state."""
        redis = await self._get_redis()
        key = self._get_state_key(phone)
        
        current_state = await self.get_state(phone)
        current_state.update(new_data)
        
        await redis.set(key, json.dumps(current_state), ex=settings.redis_session_ttl)

    async def update_stage(self, phone: str, stage: str) -> None:
        """Convenience method to update only the stage key in the state."""
        await self.update_state(phone, {"stage": stage})

    async def clear_session(self, phone: str) -> None:
        """Wipes history, transient state AND cart for a user. Call on order completion or admin reset."""
        redis = await self._get_redis()
        await redis.delete(
            self._get_history_key(phone),
            self._get_state_key(phone),
            self._get_cart_key(phone)
        )
