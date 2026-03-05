import logging
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import sessionmaker

from app.core.dependencies import (
    get_session_factory,
    get_thread_chat_service,
)

logger = logging.getLogger(__name__)
from app.db.models import Thread
from app.db.repositories.summary_repository import SummaryRepository
from app.db.repositories.thread_repository import MessageRepository, ThreadRepository
from app.domain.services.summary_service import (
    GLOBAL_LEVEL,
    LOCAL_LEVEL,
)
from app.domain.services.thread_chat_service import ThreadChatService, ThreadNotFoundError
from app.schemas.thread import (
    MessageCreate,
    MessageRead,
    SummaryRead,
    ThreadCreate,
    ThreadRead,
)


router = APIRouter()


def _get_thread_or_404(repo: ThreadRepository, thread_id: int) -> Thread:
    thread = repo.get_thread(thread_id)
    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        )
    return thread


@router.post(
    "/threads",
    response_model=ThreadRead,
    status_code=status.HTTP_201_CREATED,
)
def create_thread(
    payload: ThreadCreate,
    session_factory: sessionmaker = Depends(get_session_factory),
) -> ThreadRead:
    db = session_factory()
    try:
        thread_repo = ThreadRepository(db)
        current_model = payload.initial_model
        thread = thread_repo.create_thread(
            system_prompt=payload.system_prompt,
            title=payload.title,
            current_model=current_model,
        )
        db.commit()
        db.refresh(thread)
        return ThreadRead.model_validate(thread)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.get("/threads", response_model=List[ThreadRead])
def list_threads(
    offset: int = 0,
    limit: int = 50,
    session_factory: sessionmaker = Depends(get_session_factory),
) -> List[ThreadRead]:
    db = session_factory()
    try:
        thread_repo = ThreadRepository(db)
        threads = thread_repo.list_threads(offset=offset, limit=limit)
        return [ThreadRead.model_validate(t) for t in threads]
    finally:
        db.close()


@router.get("/threads/{thread_id}", response_model=ThreadRead)
def get_thread(
    thread_id: int,
    session_factory: sessionmaker = Depends(get_session_factory),
) -> ThreadRead:
    db = session_factory()
    try:
        thread_repo = ThreadRepository(db)
        thread = _get_thread_or_404(thread_repo, thread_id)
        return ThreadRead.model_validate(thread)
    finally:
        db.close()


@router.get("/threads/{thread_id}/messages", response_model=List[MessageRead])
def list_thread_messages(
    thread_id: int,
    limit: int = 100,
    since_id: Optional[int] = None,
    session_factory: sessionmaker = Depends(get_session_factory),
) -> List[MessageRead]:
    db = session_factory()
    try:
        thread_repo = ThreadRepository(db)
        _get_thread_or_404(thread_repo, thread_id)
        message_repo = MessageRepository(db)
        messages = message_repo.list_messages(
            thread_id=thread_id,
            since_id=since_id,
            limit=limit,
        )
        return [MessageRead.model_validate(m) for m in messages]
    finally:
        db.close()


@router.post(
    "/threads/{thread_id}/messages",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def post_message(
    thread_id: int,
    payload: MessageCreate,
    thread_chat_service: ThreadChatService = Depends(get_thread_chat_service),
) -> dict:
    try:
        result = await thread_chat_service.post_message(thread_id=thread_id, payload=payload)
    except ThreadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except httpx.HTTPStatusError as exc:
        logger.error("LLM upstream error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM provider returned {exc.response.status_code}: {exc.response.text}",
        ) from exc
    except (httpx.RequestError, RuntimeError) as exc:
        logger.error("LLM request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM request failed: {exc}",
        ) from exc

    return {
        "user_message": MessageRead.model_validate(result["user_message"]),
        "assistant_message": MessageRead.model_validate(result["assistant_message"]),
        "model_used": result["model_used"],
    }


@router.get(
    "/threads/{thread_id}/summaries",
    response_model=List[SummaryRead],
)
def list_thread_summaries(
    thread_id: int,
    session_factory: sessionmaker = Depends(get_session_factory),
) -> List[SummaryRead]:
    db = session_factory()
    try:
        thread_repo = ThreadRepository(db)
        _get_thread_or_404(thread_repo, thread_id)
        summary_repo = SummaryRepository(db)
        locals_level = summary_repo.list_summaries_by_level(
            thread_id=thread_id,
            level=LOCAL_LEVEL,
        )
        globals_level = summary_repo.list_summaries_by_level(
            thread_id=thread_id,
            level=GLOBAL_LEVEL,
        )
        all_summaries = sorted(
            [*locals_level, *globals_level],
            key=lambda s: (s.created_at, s.id),
        )
        return [SummaryRead.model_validate(s) for s in all_summaries]
    finally:
        db.close()


@router.post(
    "/threads/{thread_id}/summaries/refresh",
    response_model=None,
    status_code=status.HTTP_202_ACCEPTED,
)
async def refresh_summary(
    thread_id: int,
    thread_chat_service: ThreadChatService = Depends(get_thread_chat_service),
) -> None:
    try:
        thread_chat_service.refresh_summary(thread_id)
    except ThreadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
