from collections.abc import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.container import ServiceContainer
from app.core.container import build_container
from app.db.base import SessionLocal, get_db_session
from app.domain.services.llm_router import LLMRouter
from app.domain.services.thread_chat_service import ThreadChatService
from app.integration.model_registry import ModelCatalog, RoutingPolicy


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session.
    Use for async route handlers; sync handlers use get_session_factory and create the session inside the route.
    """
    yield from get_db_session()


def get_session_factory() -> sessionmaker:
    """Returns the sessionmaker so sync route handlers can create a session in their own thread."""
    return SessionLocal


def get_service_container(request: Request) -> ServiceContainer:
    if not hasattr(request.app.state, "container"):
        settings = get_settings()
        request.app.state.container = build_container(
            settings=settings,
            session_factory=SessionLocal,
        )
    return request.app.state.container


def get_model_catalog(
    container: ServiceContainer = Depends(get_service_container),
) -> ModelCatalog:
    return container.model_catalog


def get_routing_policy(
    container: ServiceContainer = Depends(get_service_container),
) -> RoutingPolicy:
    return container.routing_policy


def get_llm_router(
    container: ServiceContainer = Depends(get_service_container),
) -> LLMRouter:
    return container.llm_router


def get_thread_chat_service(
    container: ServiceContainer = Depends(get_service_container),
) -> ThreadChatService:
    return container.make_thread_chat_service()

