from __future__ import annotations
import json
import logging
import asyncio
from typing import Any
from redis.asyncio import Redis
from app.core.config import get_settings

log = logging.getLogger("nebula.redis")

class RedisBus:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.redis: Redis | None = None

    async def connect(self) -> None:
        if self.settings.redis_url:
            self.redis = Redis.from_url(self.settings.redis_url, decode_responses=True)

    async def close(self) -> None:
        if self.redis:
            await self.redis.close()

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        if not self.redis:
            return
        await self.redis.publish(channel, json.dumps(payload))

    async def subscribe(self, channel: str, handler):
        if not self.redis:
            return
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message and message.get("type") == "message":
                    data = json.loads(message["data"])
                    await handler(data)
        finally:
            await pubsub.unsubscribe(channel)

redis_bus = RedisBus()
