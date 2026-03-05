from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class LLMResponse:
    content: str
    model_used: str
    raw: dict[str, Any]
    latency_ms: int


class LLMProvider(Protocol):
    """
    Abstract interface for any LLM backend.

    Implement this protocol to add a new provider.
    Providers receive typed ChatMessage objects and return a normalized LLMResponse.
    """

    name: str

    async def chat(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> LLMResponse: ...
