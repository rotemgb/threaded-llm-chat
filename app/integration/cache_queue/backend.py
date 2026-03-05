import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Optional, Protocol

from app.integration.cache_queue.fingerprint import RequestFingerprint


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CacheQueueBackend(Protocol):
    """
    Abstraction for cache + coalescing backend.

    Implementations can be in-memory, Redis, etc.
    """

    def build_key(self, fingerprint: RequestFingerprint) -> str: ...

    async def get_cached(self, key: str) -> Optional[Any]: ...

    async def set_cached(self, key: str, value: Any) -> None: ...

    async def get_or_enqueue(
        self, key: str, worker_factory: "Callable[[], Awaitable[Any]] | None"
    ) -> Any: ...


@dataclass
class CacheEntry:
    value: Any
    expires_at: datetime


class InMemoryCacheQueue(CacheQueueBackend):
    """
    Simple in-memory cache with coalescing of identical in-flight requests.

    Not intended for multi-process deployments, but sufficient for this assessment.
    """

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._ttl = ttl_seconds
        self._cache: dict[str, CacheEntry] = {}
        self._in_flight: dict[str, asyncio.Future[Any]] = {}
        self._lock = asyncio.Lock()

    def build_key(self, fingerprint: RequestFingerprint) -> str:
        return fingerprint.to_hash()

    async def get_cached(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if not entry:
            return None
        if entry.expires_at <= _now():
            del self._cache[key]
            return None
        return entry.value

    async def set_cached(self, key: str, value: Any) -> None:
        self._cache[key] = CacheEntry(
            value=value,
            expires_at=_now() + timedelta(seconds=self._ttl),
        )

    async def get_or_enqueue(
        self,
        key: str,
        worker_factory: "Callable[[], Awaitable[Any]] | None" = None,
    ) -> Any:
        """
        If a result is cached, return it.
        If an identical request is in flight, await its result.
        Otherwise, lazily create and register a worker task as the in-flight owner.
        """
        cached = await self.get_cached(key)
        if cached is not None:
            return cached

        is_owner = False
        async with self._lock:
            cached = await self.get_cached(key)
            if cached is not None:
                return cached

            if key in self._in_flight:
                future = self._in_flight[key]
            else:
                if worker_factory is None:
                    raise RuntimeError("Worker factory must be provided for new keys")
                future = asyncio.create_task(worker_factory())
                self._in_flight[key] = future
                is_owner = True

        try:
            result = await future
            if is_owner:
                await self.set_cached(key, result)
            return result
        finally:
            if is_owner:
                async with self._lock:
                    self._in_flight.pop(key, None)

