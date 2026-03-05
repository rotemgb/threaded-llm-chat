from tests.model_config import TEST_MODEL_ALIASES


def test_health_ok(client) -> None:
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_models_endpoint_returns_list(client) -> None:
    response = client.get("/health/models")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert set(TEST_MODEL_ALIASES).issubset(set(data))
    assert "summarization" not in data
