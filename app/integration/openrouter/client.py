import time
from typing import Any

import httpx

from app.integration.llm_provider import ChatMessage, LLMProvider, LLMResponse


class OpenRouterProvider(LLMProvider):
    """OpenRouter-backed provider implementation."""

    name = "openrouter"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds

    async def chat(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 512,
        **_: Any,
    ) -> LLMResponse:
        if not self._api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")

        url = f"{self._base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "threaded-llm-chat",
        }
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        latency_ms = int((time.monotonic() - t0) * 1000)

        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("OpenRouter returned no choices")

        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError("Unexpected response format from OpenRouter")

        model_used = data.get("model", model)

        return LLMResponse(
            content=content,
            model_used=model_used,
            raw=data,
            latency_ms=latency_ms,
        )
