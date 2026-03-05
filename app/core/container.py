from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.sqlalchemy_uow import SqlAlchemyUnitOfWork
from app.domain.services.llm_router import LLMRouter
from app.domain.services.thread_chat_service import ThreadChatService
from app.integration.cache_queue.backend import CacheQueueBackend, InMemoryCacheQueue
from app.integration.llm_provider import LLMProvider
from app.integration.model_registry import ModelCatalog, RoutingPolicy
from app.integration.openrouter.client import OpenRouterProvider


@dataclass
class ServiceContainer:
    settings: Settings
    session_factory: sessionmaker
    model_catalog: ModelCatalog
    routing_policy: RoutingPolicy
    providers: dict[str, LLMProvider]
    cache_backend: CacheQueueBackend
    llm_router: LLMRouter

    def make_uow(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self.session_factory)

    def make_thread_chat_service(self) -> ThreadChatService:
        return ThreadChatService(
            uow_factory=self.make_uow,
            session_factory=self.session_factory,
            llm_router=self.llm_router,
            model_catalog=self.model_catalog,
            routing_policy=self.routing_policy,
        )


def _build_providers(settings: Settings) -> dict[str, LLMProvider]:
    if settings.llm_provider_backend == "openrouter":
        provider = OpenRouterProvider(
            api_key=settings.openrouter_api_key or "",
            base_url=settings.openrouter_base_url,
            timeout_seconds=settings.openrouter_timeout_seconds,
        )
        return {provider.name: provider}

    raise ValueError(
        "Unsupported LLM_PROVIDER_BACKEND. "
        f"Received '{settings.llm_provider_backend}'."
    )


def _build_cache_backend(settings: Settings) -> CacheQueueBackend:
    if settings.cache_backend == "inmemory":
        return InMemoryCacheQueue(ttl_seconds=settings.cache_ttl_seconds)

    raise ValueError(
        "Unsupported CACHE_BACKEND. "
        f"Received '{settings.cache_backend}'."
    )


def build_container(
    settings: Settings, session_factory: sessionmaker
) -> ServiceContainer:
    model_catalog = ModelCatalog(settings)
    configured_aliases = model_catalog.list_aliases(include_internal=True)
    default_alias = settings.default_chat_model_alias or configured_aliases[0]
    if not model_catalog.has_alias(default_alias):
        raise ValueError(
            "DEFAULT_CHAT_MODEL_ALIAS must be one of MODELS aliases. "
            f"Received '{default_alias}', available aliases: {configured_aliases}"
        )
    routing_policy = RoutingPolicy(default_model_key=default_alias)
    providers = _build_providers(settings)
    cache_backend = _build_cache_backend(settings)
    llm_router = LLMRouter(
        providers=providers,
        model_catalog=model_catalog,
        routing_policy=routing_policy,
        cache_queue=cache_backend,
    )
    return ServiceContainer(
        settings=settings,
        session_factory=session_factory,
        model_catalog=model_catalog,
        routing_policy=routing_policy,
        providers=providers,
        cache_backend=cache_backend,
        llm_router=llm_router,
    )
