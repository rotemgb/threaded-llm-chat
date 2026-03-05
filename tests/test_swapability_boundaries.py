import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.container import build_container
from app.db.base import SessionLocal
from app.integration.cache_queue.backend import InMemoryCacheQueue
from app.integration.cache_queue.fingerprint import RequestFingerprint
from app.integration.model_registry import ModelCatalog, RoutingPolicy
from tests.model_config import (
    TEST_DEFAULT_CHAT_MODEL_ALIAS,
    TEST_MODEL_ALIASES,
    TEST_MODELS_JSON,
)


def test_model_catalog_from_required_models_json():
    catalog = ModelCatalog(
        Settings(
            models_json=TEST_MODELS_JSON,
            default_chat_model_alias=TEST_DEFAULT_CHAT_MODEL_ALIAS,
        )
    )
    aliases = catalog.list_aliases(include_internal=True)
    assert set(TEST_MODEL_ALIASES).issubset(set(aliases))


def test_routing_policy_prefers_requested_then_thread_then_default():
    policy = RoutingPolicy(default_model_key=TEST_DEFAULT_CHAT_MODEL_ALIAS)
    assert (
        policy.resolve_chat_model_key(
            requested_model_key=TEST_MODEL_ALIASES[1],
            thread_default_model_key=TEST_MODEL_ALIASES[0],
        )
        == TEST_MODEL_ALIASES[1]
    )
    assert (
        policy.resolve_chat_model_key(
            requested_model_key=None,
            thread_default_model_key=TEST_MODEL_ALIASES[1],
        )
        == TEST_MODEL_ALIASES[1]
    )
    assert (
        policy.resolve_chat_model_key(
            requested_model_key=None,
            thread_default_model_key=None,
        )
        == TEST_DEFAULT_CHAT_MODEL_ALIAS
    )


def test_request_fingerprint_changes_with_generation_params():
    base = RequestFingerprint(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}],
        params={"temperature": 0.2},
    )
    modified = RequestFingerprint(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}],
        params={"temperature": 0.8},
    )
    assert base.to_hash() != modified.to_hash()


def test_container_builds_swappable_boundaries():
    container = build_container(
        Settings(
            models_json=TEST_MODELS_JSON,
            default_chat_model_alias=TEST_DEFAULT_CHAT_MODEL_ALIAS,
        ),
        SessionLocal,
    )
    assert container.llm_router is not None
    assert container.make_uow() is not None
    assert container.make_thread_chat_service() is not None


def test_container_uses_configured_provider_and_cache_defaults():
    container = build_container(
        Settings(
            models_json=TEST_MODELS_JSON,
            default_chat_model_alias=TEST_DEFAULT_CHAT_MODEL_ALIAS,
        ),
        SessionLocal,
    )
    assert "openrouter" in container.providers
    assert isinstance(container.cache_backend, InMemoryCacheQueue)


def test_invalid_llm_provider_backend_fails_fast():
    with pytest.raises(ValidationError):
        Settings(
            models_json=TEST_MODELS_JSON,
            default_chat_model_alias=TEST_DEFAULT_CHAT_MODEL_ALIAS,
            llm_provider_backend="bad_provider",
        )


def test_invalid_cache_backend_fails_fast():
    with pytest.raises(ValidationError):
        Settings(
            models_json=TEST_MODELS_JSON,
            default_chat_model_alias=TEST_DEFAULT_CHAT_MODEL_ALIAS,
            cache_backend="bad_cache",
        )


def test_non_positive_cache_ttl_fails_fast():
    with pytest.raises(ValidationError):
        Settings(
            models_json=TEST_MODELS_JSON,
            default_chat_model_alias=TEST_DEFAULT_CHAT_MODEL_ALIAS,
            cache_ttl_seconds=0,
        )
