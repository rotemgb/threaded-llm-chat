"""Integration tests for thread management, messages, model switching, and summaries."""

from tests.model_config import TEST_MODEL_ALIASES


def _create_thread(
    client, title="Test thread", system_prompt="You are a test assistant."
):
    res = client.post(
        "/threads",
        json={"system_prompt": system_prompt, "title": title},
    )
    assert res.status_code == 201
    return res.json()


# ---------------------------------------------------------------------------
# Thread CRUD
# ---------------------------------------------------------------------------


def test_create_thread(client, mock_llm):
    thread = _create_thread(client)
    assert thread["title"] == "Test thread"
    assert thread["system_prompt"] == "You are a test assistant."
    assert "id" in thread
    assert "created_at" in thread


def test_list_threads(client, mock_llm):
    _create_thread(client, title="Thread A")
    _create_thread(client, title="Thread B")
    res = client.get("/threads")
    assert res.status_code == 200
    titles = [t["title"] for t in res.json()]
    assert "Thread A" in titles
    assert "Thread B" in titles


def test_get_thread(client, mock_llm):
    thread = _create_thread(client)
    res = client.get(f"/threads/{thread['id']}")
    assert res.status_code == 200
    assert res.json()["id"] == thread["id"]


def test_get_thread_404(client, mock_llm):
    res = client.get("/threads/999999")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


def test_post_message_and_get_reply(client, mock_llm):
    thread = _create_thread(client)
    res = client.post(
        f"/threads/{thread['id']}/messages",
        json={"content": "Hello", "sender": "user"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["assistant_message"]["content"] == "mock reply"
    assert body["model_used"] == "test-model"


def test_message_history(client, mock_llm):
    thread = _create_thread(client)
    client.post(
        f"/threads/{thread['id']}/messages",
        json={"content": "First message", "sender": "user"},
    )
    client.post(
        f"/threads/{thread['id']}/messages",
        json={"content": "Second message", "sender": "user"},
    )
    res = client.get(f"/threads/{thread['id']}/messages?limit=200")
    assert res.status_code == 200
    messages = res.json()
    assert len(messages) == 4  # 2 user + 2 assistant
    roles = [m["role"] for m in messages]
    assert roles == ["user", "assistant", "user", "assistant"]


def test_post_message_thread_not_found(client, mock_llm):
    res = client.post(
        "/threads/999999/messages",
        json={"content": "Hello", "sender": "user"},
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Model switching
# ---------------------------------------------------------------------------


def test_model_switching(client, mock_llm):
    """Posting messages with different model choices passes the choice through."""
    thread = _create_thread(client)

    client.post(
        f"/threads/{thread['id']}/messages",
        json={
            "content": "Use primary",
            "sender": "user",
            "model": TEST_MODEL_ALIASES[0],
        },
    )
    assert mock_llm[-1]["model_choice"] == TEST_MODEL_ALIASES[0]

    client.post(
        f"/threads/{thread['id']}/messages",
        json={
            "content": "Use quality",
            "sender": "user",
            "model": TEST_MODEL_ALIASES[1],
        },
    )
    assert mock_llm[-1]["model_choice"] == TEST_MODEL_ALIASES[1]


def test_unknown_model_returns_422(client, mock_llm):
    """Requesting an unknown model alias returns 422 with available models."""
    thread = _create_thread(client)
    res = client.post(
        f"/threads/{thread['id']}/messages",
        json={"content": "Hello", "sender": "user", "model": "nonexistent"},
    )
    assert res.status_code == 422
    assert "nonexistent" in res.json()["detail"]


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


def test_summaries_empty(client, mock_llm):
    thread = _create_thread(client)
    res = client.get(f"/threads/{thread['id']}/summaries")
    assert res.status_code == 200
    assert res.json() == []


def test_summaries_after_messages(client, mock_llm):
    """After enough messages, auto-summarization should create at least one summary."""
    thread = _create_thread(client)
    for i in range(12):
        client.post(
            f"/threads/{thread['id']}/messages",
            json={"content": f"Message {i}", "sender": "user"},
        )
    res = client.get(f"/threads/{thread['id']}/summaries")
    assert res.status_code == 200
    summaries = res.json()
    assert len(summaries) >= 1
    assert summaries[0]["thread_id"] == thread["id"]
    assert summaries[0]["summary_text"]
