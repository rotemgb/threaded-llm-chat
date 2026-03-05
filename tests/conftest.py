import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.container import build_container
from app.core.dependencies import get_db, get_service_container, get_session_factory
from app.db.base import Base
from app.main import app
from tests.model_config import TEST_DEFAULT_CHAT_MODEL_ALIAS, TEST_MODELS_JSON


_test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


def _override_get_session_factory():
    return _TestSession


@pytest.fixture(autouse=True)
def _setup_test_db():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture()
def client():
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_session_factory] = _override_get_session_factory
    app.dependency_overrides[get_service_container] = lambda: build_container(
        settings=Settings(
            models_json=TEST_MODELS_JSON,
            default_chat_model_alias=TEST_DEFAULT_CHAT_MODEL_ALIAS,
        ),
        session_factory=_TestSession,
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def mock_llm(monkeypatch):
    """Patch LLMRouter.chat so tests never call OpenRouter."""
    from app.integration.llm_provider import LLMResponse
    from app.integration.model_registry import ModelSpec

    _fake_spec = ModelSpec(provider="openrouter", model="test-model")

    call_log: list[dict] = []

    async def fake_chat(
        self, *, model_key=None, messages, default_model_key=None, **kwargs
    ):
        call_log.append(
            {
                "model_choice": model_key,
                "messages_window": messages,
                "default_model_key": default_model_key,
            }
        )
        return (
            LLMResponse(
                content="mock reply",
                model_used="test-model",
                raw={},
                latency_ms=1,
            ),
            _fake_spec,
        )

    from app.domain.services import llm_router

    monkeypatch.setattr(
        llm_router.LLMRouter,
        "chat",
        fake_chat,
    )
    return call_log
