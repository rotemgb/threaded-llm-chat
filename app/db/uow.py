from __future__ import annotations

from typing import Protocol

from app.db.repositories.summary_repository import SummaryRepository
from app.db.repositories.thread_repository import MessageRepository, ThreadRepository


class UnitOfWork(Protocol):
    thread_repo: ThreadRepository
    message_repo: MessageRepository
    summary_repo: SummaryRepository

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def close(self) -> None: ...
