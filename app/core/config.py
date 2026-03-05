from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    openrouter_api_key: str | None = None

    @field_validator("openrouter_api_key", mode="before")
    @classmethod
    def strip_openrouter_api_key(cls, v: str | None) -> str | None:
        if v is None or not isinstance(v, str):
            return v
        return v.strip() or None

    database_url: str = "sqlite:///./app.db"

    llm_provider_backend: str = Field(
        default="openrouter",
        validation_alias="LLM_PROVIDER_BACKEND",
    )
    cache_backend: str = Field(
        default="inmemory",
        validation_alias="CACHE_BACKEND",
    )
    cache_ttl_seconds: int = Field(
        default=300,
        validation_alias="CACHE_TTL_SECONDS",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias="OPENROUTER_BASE_URL",
    )
    openrouter_timeout_seconds: float = Field(
        default=30.0,
        validation_alias="OPENROUTER_TIMEOUT_SECONDS",
    )

    @field_validator("llm_provider_backend", "cache_backend", mode="before")
    @classmethod
    def strip_backend_values(cls, v: str | None) -> str | None:
        if v is None or not isinstance(v, str):
            return v
        value = v.strip().lower()
        return value or None

    @field_validator("llm_provider_backend")
    @classmethod
    def validate_llm_provider_backend(cls, v: str) -> str:
        allowed = {"openrouter"}
        if v not in allowed:
            raise ValueError(
                f"LLM_PROVIDER_BACKEND must be one of {sorted(allowed)}; received '{v}'"
            )
        return v

    @field_validator("cache_backend")
    @classmethod
    def validate_cache_backend(cls, v: str) -> str:
        allowed = {"inmemory"}
        if v not in allowed:
            raise ValueError(
                f"CACHE_BACKEND must be one of {sorted(allowed)}; received '{v}'"
            )
        return v

    @field_validator("cache_ttl_seconds")
    @classmethod
    def validate_cache_ttl_seconds(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("CACHE_TTL_SECONDS must be > 0")
        return v

    @field_validator("openrouter_base_url", mode="before")
    @classmethod
    def strip_openrouter_base_url(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("OPENROUTER_BASE_URL must be a non-empty string")
        return value

    @field_validator("openrouter_timeout_seconds")
    @classmethod
    def validate_openrouter_timeout_seconds(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("OPENROUTER_TIMEOUT_SECONDS must be > 0")
        return v

    # Dynamic model registry: JSON mapping alias -> "provider/model".
    # Example: {"primary":"openrouter/openai/gpt-4o-mini","quality":"openrouter/anthropic/claude-3.5-sonnet"}
    models_json: str | None = Field(default=None, validation_alias="MODELS")
    default_chat_model_alias: str | None = Field(
        default=None, validation_alias="DEFAULT_CHAT_MODEL_ALIAS"
    )

    @field_validator("default_chat_model_alias", mode="before")
    @classmethod
    def strip_default_chat_model_alias(cls, v: str | None) -> str | None:
        if v is None or not isinstance(v, str):
            return v
        return v.strip() or None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
