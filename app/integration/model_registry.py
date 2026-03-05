"""
Provider-agnostic model registry.

Models are resolved from the ``MODELS`` env var (JSON dict) when set,
and must be explicitly configured.

Each entry maps an alias (e.g. ``"primary"``) to a ``ModelSpec``
containing a *provider* name and the *model* to pass to that provider.

Convention for the ``MODELS`` JSON values:
    ``"<provider>/<model>"``
    e.g. ``"openrouter/openai/gpt-4o"``   -> provider=openrouter, model=openai/gpt-4o
         ``"ollama/llama3"``               -> provider=ollama,     model=llama3
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str


class ModelCatalog:
    """
    Class-based model registry:
    - parses config once
    - resolves model aliases
    - exposes user-selectable aliases
    """

    def __init__(self, settings: Settings) -> None:
        self._models = self._build_models(settings)

    @staticmethod
    def _parse_provider_model(raw: str) -> tuple[str, str]:
        parts = raw.split("/", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(
                f"Invalid model value '{raw}': expected 'provider/model_id' "
                "(e.g. 'openrouter/openai/gpt-4o')"
            )
        return parts[0], parts[1]

    def _build_models(self, settings: Settings) -> dict[str, ModelSpec]:
        if not settings.models_json:
            raise ValueError(
                "MODELS is required but not set. "
                "Provide MODELS as JSON mapping alias -> 'provider/model' "
                "(e.g. {\"primary\":\"openrouter/openai/gpt-4o-mini\",\"quality\":\"openrouter/anthropic/claude-3.5-sonnet\"})."
            )

        parsed: Any = json.loads(settings.models_json)
        if not isinstance(parsed, dict):
            raise ValueError("MODELS must be a JSON object: alias -> provider/model")

        registry: dict[str, ModelSpec] = {}
        for alias, value in parsed.items():
            if not isinstance(alias, str) or not alias.strip():
                raise ValueError("MODELS keys must be non-empty strings")
            if not isinstance(value, str):
                raise ValueError(f"MODELS['{alias}'] must be a string")
            provider, model = self._parse_provider_model(value)
            registry[alias] = ModelSpec(provider=provider, model=model)

        if not registry:
            raise ValueError("MODELS must include at least one alias")
        return registry

    def resolve(self, model_key: str) -> ModelSpec:
        if model_key not in self._models:
            available = sorted(self._models.keys())
            raise ValueError(f"Unknown model '{model_key}'. Available: {available}")
        return self._models[model_key]

    def list_aliases(self, include_internal: bool = False) -> list[str]:
        aliases = sorted(self._models.keys())
        if include_internal:
            return aliases
        return [k for k in aliases if k != "summarization"]

    def has_alias(self, alias: str) -> bool:
        return alias in self._models


class RoutingPolicy:
    """
    Encapsulates model-key selection policy (defaults + special-purpose keys).
    """

    def __init__(self, default_model_key: str) -> None:
        self._default_model_key = default_model_key

    def resolve_chat_model_key(
        self,
        requested_model_key: str | None,
        thread_default_model_key: str | None = None,
    ) -> str:
        return (
            requested_model_key or thread_default_model_key or self._default_model_key
        )

    def resolve_summarization_model_key(
        self, model_catalog: ModelCatalog
    ) -> str | None:
        return "summarization" if model_catalog.has_alias("summarization") else None


# Backward-compatible alias used by existing call sites during refactor rollout.
ModelRegistry = ModelCatalog
