from __future__ import annotations

from typing import Any

from app.integration.cache_queue.fingerprint import RequestFingerprint
from app.integration.cache_queue.backend import CacheQueueBackend, InMemoryCacheQueue
from app.integration.llm_provider import ChatMessage, LLMProvider, LLMResponse
from app.integration.model_registry import ModelCatalog, ModelSpec, RoutingPolicy


class LLMRouter:
    """
    Resolves model aliases through ModelRegistry and dispatches to providers.
    Keeps cache/coalescing semantics via CacheQueueBackend.
    """

    def __init__(
        self,
        providers: dict[str, LLMProvider],
        model_catalog: ModelCatalog,
        routing_policy: RoutingPolicy,
        cache_queue: CacheQueueBackend | None = None,
    ) -> None:
        self._providers = providers
        self._model_catalog = model_catalog
        self._routing_policy = routing_policy
        self._cache_queue: CacheQueueBackend = cache_queue or InMemoryCacheQueue()

    def _get_provider(self, name: str) -> LLMProvider:
        provider = self._providers.get(name)
        if provider is None:
            available = sorted(self._providers.keys())
            raise RuntimeError(
                f"No provider registered for '{name}'. "
                f"Available providers: {available}"
            )
        return provider

    async def chat(
        self,
        *,
        model_key: str | None,
        messages: list[ChatMessage],
        default_model_key: str | None = None,
        **kwargs: Any,
    ) -> tuple[LLMResponse, ModelSpec]:
        resolved_model_key = self._routing_policy.resolve_chat_model_key(
            requested_model_key=model_key,
            thread_default_model_key=default_model_key,
        )
        spec = self._model_catalog.resolve(resolved_model_key)
        provider = self._get_provider(spec.provider)
        fingerprint = RequestFingerprint(
            model=spec.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            params=kwargs,
        )
        cache_key = self._cache_queue.build_key(fingerprint)

        async def _worker() -> LLMResponse:
            return await provider.chat(
                model=spec.model,
                messages=messages,
                **kwargs,
            )

        llm_response: LLMResponse = await self._cache_queue.get_or_enqueue(
            cache_key, worker_factory=_worker
        )
        return llm_response, spec


LLMOrchestrator = LLMRouter
