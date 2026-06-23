from __future__ import annotations
from dataclasses import dataclass
from time import monotonic
from collections import defaultdict, deque
from fastapi import Request, WebSocket

@dataclass
class Bucket:
    timestamps: deque

class RateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self.ip_buckets: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = monotonic()
        bucket = self.ip_buckets[key]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False
        bucket.append(now)
        return True

limiter = RateLimiter(limit=120, window_seconds=60)

async def enforce_http_rate_limit(request: Request) -> None:
    key = request.client.host if request.client else "unknown"
    if not limiter.allow(key):
        from fastapi import HTTPException
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

async def enforce_ws_rate_limit(websocket: WebSocket) -> None:
    key = websocket.client.host if websocket.client else "unknown"
    if not limiter.allow(f"ws:{key}"):
        await websocket.close(code=4408)
        raise RuntimeError("Rate limit exceeded")
