from typing import Optional, Sequence

from app.db.models import Summary, Thread
from app.db.repositories.summary_repository import SummaryRepository
from app.db.repositories.thread_repository import MessageRepository
from app.domain.services.llm_router import LLMOrchestrator
from app.integration.llm_provider import ChatMessage


LOCAL_LEVEL = 1
GLOBAL_LEVEL = 2


class SummaryService:
    def __init__(
        self,
        message_repo: MessageRepository,
        summary_repo: SummaryRepository,
        orchestrator: LLMOrchestrator,
        summarization_model_key: str | None = None,
        messages_per_local_summary: int = 10,
        locals_per_global_summary: int = 3,
    ) -> None:
        self._message_repo = message_repo
        self._summary_repo = summary_repo
        self._orchestrator = orchestrator
        self._summarization_model_key = summarization_model_key
        self._messages_per_local_summary = messages_per_local_summary
        self._locals_per_global_summary = locals_per_global_summary

    async def maybe_summarize(self, thread: Thread) -> None:
        """
        Perform hierarchical summarization:
        - Level 1: local/chunk summaries after K new messages.
        - Level 2: global summary after M new local summaries.
        """
        local_created = await self._maybe_create_local_summary(thread)
        if local_created:
            await self._maybe_create_global_summary(thread)

    async def _maybe_create_local_summary(self, thread: Thread) -> bool:
        latest_local = self._summary_repo.get_latest_summary(
            thread_id=thread.id, level=LOCAL_LEVEL
        )
        since_id = (
            latest_local.covers_up_to_message_id if latest_local is not None else None
        )
        new_messages = list(
            self._message_repo.list_messages(
                thread_id=thread.id,
                since_id=since_id,
                limit=1000,
            )
        )

        if len(new_messages) < self._messages_per_local_summary:
            return False

        convo_text = ""
        for msg in new_messages:
            prefix = msg.role.upper()
            convo_text += f"{prefix}: {msg.content}\n"

        prompt = (
            "Summarize the following segment of a conversation. "
            "Focus on concrete facts, decisions, user goals, and open questions:\n\n"
            f"{convo_text}"
        )

        context = [
            ChatMessage(
                role="system",
                content="You are a helpful assistant that creates concise summaries of conversation segments.",
            ),
            ChatMessage(role="user", content=prompt),
        ]

        llm_response, _model = await self._orchestrator.chat(
            model_key=self._summarization_model_key,
            default_model_key=thread.current_model,
            messages=context,
        )
        summary_text = llm_response.content

        last_message_id = new_messages[-1].id
        self._summary_repo.add_summary(
            thread_id=thread.id,
            summary_text=summary_text,
            level=LOCAL_LEVEL,
            covers_up_to_message_id=last_message_id,
        )

        return True

    async def _maybe_create_global_summary(self, thread: Thread) -> None:
        latest_global = self._summary_repo.get_latest_summary(
            thread_id=thread.id, level=GLOBAL_LEVEL
        )

        after_created_at = (
            latest_global.created_at if latest_global is not None else None
        )
        new_locals: Sequence[Summary] = self._summary_repo.list_summaries_by_level(
            thread_id=thread.id,
            level=LOCAL_LEVEL,
            after_created_at=after_created_at,
        )

        if len(new_locals) < self._locals_per_global_summary:
            return

        pieces = []
        if latest_global is not None:
            pieces.append(f"Previous global summary:\n{latest_global.summary_text}\n")

        pieces.append("New local summaries:\n")
        for local in new_locals:
            pieces.append(f"- {local.summary_text}")

        prompt = (
            "Given the following previous global summary (if any) and new local summaries, "
            "produce an updated, high-level summary of the entire conversation so far. "
            "Keep it concise and focused on user goals, major decisions, and open issues.\n\n"
            + "\n".join(pieces)
        )

        context = [
            ChatMessage(
                role="system",
                content="You are a helpful assistant that maintains a concise, high-level summary of a long conversation.",
            ),
            ChatMessage(role="user", content=prompt),
        ]

        llm_response, _model = await self._orchestrator.chat(
            model_key=self._summarization_model_key,
            default_model_key=thread.current_model,
            messages=context,
        )
        summary_text = llm_response.content

        last_local = new_locals[-1]
        covers_up_to = last_local.covers_up_to_message_id

        self._summary_repo.add_summary(
            thread_id=thread.id,
            summary_text=summary_text,
            level=GLOBAL_LEVEL,
            covers_up_to_message_id=covers_up_to,
        )
