from __future__ import annotations

import asyncio
from collections.abc import Callable

from sqlalchemy.orm import sessionmaker

from app.db.sqlalchemy_uow import SqlAlchemyUnitOfWork
from app.domain.services.context_service import ContextService
from app.domain.services.llm_router import LLMRouter
from app.domain.services.summary_service import GLOBAL_LEVEL, LOCAL_LEVEL
from app.domain.services.summary_worker import run_summary_job
from app.integration.model_registry import ModelCatalog, RoutingPolicy
from app.schemas.thread import MessageCreate


class ThreadNotFoundError(Exception):
    pass


class ThreadChatService:
    def __init__(
        self,
        uow_factory: Callable[[], SqlAlchemyUnitOfWork],
        session_factory: sessionmaker,
        llm_router: LLMRouter,
        model_catalog: ModelCatalog,
        routing_policy: RoutingPolicy,
    ) -> None:
        self._uow_factory = uow_factory
        self._session_factory = session_factory
        self._llm_router = llm_router
        self._model_catalog = model_catalog
        self._routing_policy = routing_policy
        self._context_service = ContextService()

    async def post_message(self, thread_id: int, payload: MessageCreate) -> dict:
        uow = self._uow_factory()
        try:
            thread = uow.thread_repo.get_thread(thread_id)
            if thread is None:
                raise ThreadNotFoundError("Thread not found")

            if payload.model:
                self._model_catalog.resolve(payload.model)

            user_message = uow.message_repo.add_message(
                thread_id=thread.id,
                role="user",
                content=payload.content,
                sender=payload.sender,
                model_id=None,
            )

            global_summary = uow.summary_repo.get_latest_summary(
                thread_id=thread.id,
                level=GLOBAL_LEVEL,
            )
            local_summaries = uow.summary_repo.list_summaries_by_level(
                thread_id=thread.id,
                level=LOCAL_LEVEL,
            )
            recent_messages = uow.message_repo.list_messages(
                thread_id=thread.id,
                since_id=None,
                limit=100,
            )
            context = self._context_service.build_context(
                thread=thread,
                global_summary=global_summary,
                local_summaries=local_summaries,
                recent_messages=recent_messages,
            )

            llm_response, model_spec = await self._llm_router.chat(
                model_key=payload.model,
                default_model_key=thread.current_model,
                messages=context,
            )
            assistant_message = uow.message_repo.add_message(
                thread_id=thread.id,
                role="assistant",
                content=llm_response.content,
                sender="agent",
                model_id=model_spec.model,
            )
            uow.commit()
            uow.session.refresh(user_message)
            uow.session.refresh(assistant_message)

            asyncio.create_task(
                run_summary_job(
                    thread_id=thread.id,
                    session_factory=self._session_factory,
                    llm_router=self._llm_router,
                    summarization_model_key=self._routing_policy.resolve_summarization_model_key(
                        self._model_catalog
                    ),
                ),
                name=f"summary-thread-{thread.id}",
            )

            return {
                "user_message": user_message,
                "assistant_message": assistant_message,
                "model_used": model_spec.model,
            }
        except Exception:
            uow.rollback()
            raise
        finally:
            uow.close()

    def refresh_summary(self, thread_id: int) -> None:
        uow = self._uow_factory()
        try:
            thread = uow.thread_repo.get_thread(thread_id)
            if thread is None:
                raise ThreadNotFoundError("Thread not found")
        finally:
            uow.close()

        asyncio.create_task(
            run_summary_job(
                thread_id=thread_id,
                session_factory=self._session_factory,
                llm_router=self._llm_router,
                summarization_model_key=self._routing_policy.resolve_summarization_model_key(
                    self._model_catalog
                ),
            ),
            name=f"summary-refresh-thread-{thread_id}",
        )
