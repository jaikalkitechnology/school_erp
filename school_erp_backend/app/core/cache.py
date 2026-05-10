"""Redis client wrapper with strict per-tenant key namespacing.

Every key is prefixed ``tenant:{id}:`` so a stray cross-tenant lookup is
impossible without explicit override.
"""

from __future__ import annotations

from typing import Any, Optional

from redis.asyncio import Redis, from_url

from app.config import settings

_redis: Optional[Redis] = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    return _redis


def tenant_key(tenant_id: int | None, *parts: str) -> str:
    if tenant_id is None:
        return "platform:" + ":".join(parts)
    return f"tenant:{int(tenant_id)}:" + ":".join(parts)


class TenantCache:
    """Thin wrapper that forces every key through ``tenant_key``."""

    def __init__(self, tenant_id: int | None) -> None:
        self.tenant_id = tenant_id
        self.client = get_redis()

    async def get(self, *parts: str) -> Optional[str]:
        return await self.client.get(tenant_key(self.tenant_id, *parts))

    async def set(self, value: Any, *parts: str, ttl_seconds: int | None = None) -> None:
        key = tenant_key(self.tenant_id, *parts)
        if ttl_seconds:
            await self.client.set(key, value, ex=ttl_seconds)
        else:
            await self.client.set(key, value)

    async def delete(self, *parts: str) -> None:
        await self.client.delete(tenant_key(self.tenant_id, *parts))

    async def incr(self, *parts: str) -> int:
        return int(await self.client.incr(tenant_key(self.tenant_id, *parts)))
