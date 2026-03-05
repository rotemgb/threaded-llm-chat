from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.db.repositories.summary_repository import SummaryRepository
from app.db.repositories.thread_repository import MessageRepository, ThreadRepository


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory
        self.session: Session = self._session_factory()
        self.thread_repo = ThreadRepository(self.session)
        self.message_repo = MessageRepository(self.session)
        self.summary_repo = SummaryRepository(self.session)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def close(self) -> None:
        self.session.close()
