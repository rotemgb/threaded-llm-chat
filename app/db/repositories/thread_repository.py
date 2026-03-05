from collections.abc import Sequence
from typing import Optional

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.models import Message, Thread


class ThreadRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_thread(
        self,
        system_prompt: str,
        title: Optional[str] = None,
        current_model: Optional[str] = None,
    ) -> Thread:
        thread = Thread(
            system_prompt=system_prompt,
            title=title,
            current_model=current_model,
        )
        self.session.add(thread)
        self.session.flush()
        return thread

    def get_thread(self, thread_id: int) -> Optional[Thread]:
        stmt: Select[Thread] = select(Thread).where(Thread.id == thread_id)
        return self.session.scalar(stmt)

    def list_threads(self, offset: int = 0, limit: int = 50) -> Sequence[Thread]:
        stmt: Select[Thread] = (
            select(Thread)
            .order_by(Thread.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(stmt))


class MessageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_message(
        self,
        thread_id: int,
        role: str,
        content: str,
        sender: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> Message:
        message = Message(
            thread_id=thread_id,
            role=role,
            content=content,
            sender=sender,
            model_id=model_id,
        )
        self.session.add(message)
        self.session.flush()
        return message

    def list_messages(
        self,
        thread_id: int,
        since_id: Optional[int] = None,
        limit: int = 100,
    ) -> Sequence[Message]:
        stmt: Select[Message] = (
            select(Message)
            .where(Message.thread_id == thread_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
            .limit(limit)
        )
        if since_id is not None:
            stmt = stmt.where(Message.id > since_id)
        return list(self.session.scalars(stmt))
