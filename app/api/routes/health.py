from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.core.config import get_settings
from app.core.dependencies import get_model_catalog
from app.integration.model_registry import ModelCatalog


router = APIRouter()


@router.get("/", summary="Health check")
async def health_check() -> dict:
    return {"status": "ok"}


@router.get("/openrouter", summary="Test OpenRouter API key")
async def health_openrouter() -> dict:
    """
    Verify OPENROUTER_API_KEY by calling the chat completions endpoint (which requires a valid key).
    GET /models may succeed without auth; this uses POST /chat/completions so only a valid key returns 200.
    """
    settings = get_settings()
    if not settings.openrouter_api_key or not settings.openrouter_api_key.strip():
        raise HTTPException(
            status_code=503,
            detail="OPENROUTER_API_KEY is not set in .env. Add OPENROUTER_API_KEY=sk-or-... to verify your key.",
        )
    key = settings.openrouter_api_key.strip()
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5173",
                "X-Title": "threaded-llm-chat",
            },
            json={
                "model": "openai/gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
                "max_tokens": 10,
            },
        )
    if response.status_code == 200:
        return {"status": "ok", "message": "OpenRouter key is valid"}
    raise HTTPException(
        status_code=response.status_code,
        detail=response.text or f"OpenRouter API returned {response.status_code}",
    )


@router.get("/models", summary="List available model aliases")
async def get_models(
    model_catalog: ModelCatalog = Depends(get_model_catalog),
) -> List[str]:
    """Return the list of model alias names that can be used in the ``model`` field."""
    return model_catalog.list_aliases(include_internal=False)
