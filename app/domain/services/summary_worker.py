import logging

from sqlalchemy.orm import sessionmaker

from app.db.sqlalchemy_uow import SqlAlchemyUnitOfWork
from app.domain.services.llm_router import LLMRouter
from app.domain.services.summary_service import SummaryService


logger = logging.getLogger(__name__)


async def run_summary_job(
    *,
    thread_id: int,
    session_factory: sessionmaker,
    llm_router: LLMRouter,
    summarization_model_key: str | None,
) -> None:
    """
    Background summary worker.
    Uses its own DB unit-of-work so request path can return immediately.
    """
    uow = SqlAlchemyUnitOfWork(session_factory)
    try:
        thread = uow.thread_repo.get_thread(thread_id)
        if thread is None:
            logger.warning(
                "Skipping summarization for missing thread_id=%s",
                thread_id,
            )
            return

        summary_service = SummaryService(
            message_repo=uow.message_repo,
            summary_repo=uow.summary_repo,
            orchestrator=llm_router,
            summarization_model_key=summarization_model_key,
        )
        await summary_service.maybe_summarize(thread)
        uow.commit()
    except Exception:
        uow.rollback()
        logger.exception("Background summarization failed for thread_id=%s", thread_id)
    finally:
        uow.close()
