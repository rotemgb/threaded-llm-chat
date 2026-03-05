from collections.abc import Sequence
from datetime import datetime
from typing import Optional

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.models import Summary


class SummaryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_summary(
        self,
        thread_id: int,
        summary_text: str,
        level: int = 1,
        covers_up_to_message_id: Optional[int] = None,
    ) -> Summary:
        summary = Summary(
            thread_id=thread_id,
            summary_text=summary_text,
            level=level,
            covers_up_to_message_id=covers_up_to_message_id,
        )
        self.session.add(summary)
        self.session.flush()
        return summary

    def get_latest_summary(self, thread_id: int, level: int) -> Optional[Summary]:
        stmt: Select[Summary] = (
            select(Summary)
            .where(Summary.thread_id == thread_id)
            .where(Summary.level == level)
            .order_by(Summary.created_at.desc(), Summary.id.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def list_summaries_by_level(
        self,
        thread_id: int,
        level: int,
        after_created_at: Optional[datetime] = None,
    ) -> Sequence[Summary]:
        stmt: Select[Summary] = (
            select(Summary)
            .where(Summary.thread_id == thread_id)
            .where(Summary.level == level)
            .order_by(Summary.created_at.asc(), Summary.id.asc())
        )
        if after_created_at is not None:
            stmt = stmt.where(Summary.created_at > after_created_at)
        return list(self.session.scalars(stmt))


