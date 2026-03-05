from typing import List, Optional, Sequence

from app.db.models import Message, Summary, Thread
from app.integration.llm_provider import ChatMessage


class ContextService:
    def __init__(
        self,
        max_local_summaries: int = 2,
        max_messages: int = 20,
    ) -> None:
        self._max_local_summaries = max_local_summaries
        self._max_messages = max_messages

    def build_context(
        self,
        thread: Thread,
        global_summary: Optional[Summary],
        local_summaries: Sequence[Summary],
        recent_messages: Sequence[Message],
    ) -> List[ChatMessage]:
        """
        Build OpenAI-style messages list:
        - system prompt
        - latest global (high-level) summary, if any
        - a few most recent local (chunk) summaries
        - recent raw messages
        """
        messages: List[ChatMessage] = []

        messages.append(ChatMessage(role="system", content=thread.system_prompt))

        if global_summary is not None:
            messages.append(
                ChatMessage(
                    role="system",
                    content=f"High-level summary of this conversation: {global_summary.summary_text}",
                )
            )

        tail_locals = list(local_summaries)[-self._max_local_summaries :]
        for summary in tail_locals:
            messages.append(
                ChatMessage(
                    role="system",
                    content=f"Recent chunk summary: {summary.summary_text}",
                )
            )

        tail_messages = list(recent_messages)[-self._max_messages :]
        for msg in tail_messages:
            messages.append(ChatMessage(role=msg.role, content=msg.content))

        return messages
