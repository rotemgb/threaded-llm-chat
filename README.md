# superq-chat

Multi-agent chat threading service with hierarchical summaries, built with FastAPI, SQLAlchemy, OpenRouter, and a React frontend.

## Architecture

```
Browser (React :5173)
  │
  ▼
FastAPI backend (:8000)
  ├── ServiceContainer ─ centralized dependency composition and factory boundaries
  ├── ThreadChatService ─ use-case layer for message flow orchestration
  ├── LLMRouter        ─ resolves alias via RoutingPolicy → ModelCatalog → provider
  │     └── LLMProvider protocol (OpenRouterProvider, extensible for others)
  ├── UnitOfWork       ─ transaction boundary abstraction (SQLAlchemy impl)
  ├── SummaryService   ─ hierarchical auto-summarization (local + global)
  ├── CacheQueue       ─ request fingerprint based coalescing & caching
  └── SQLite (SQLAlchemy ORM)
```

## Backend (FastAPI + uv)

- Python 3.12
- FastAPI app in `app/`
- SQLite + SQLAlchemy models in `app/db/`
- LLM provider abstraction in `app/integration/llm_provider.py` (Protocol)
- OpenRouter provider in `app/integration/openrouter/`
- Model catalog + routing policy in `app/integration/model_registry.py`
- Request/use-case boundaries in `app/core/container.py` and `app/domain/services/thread_chat_service.py`
- Hierarchical summarization and context management in `app/domain/services/`
- Dependency management via **uv** and `pyproject.toml`

### Setup

Install [uv](https://docs.astral.sh/uv/) if you don't have it yet, then:

### Run with Docker

```bash
cd superq-chat
cp env/.env.example .env
# Edit .env and set OPENROUTER_API_KEY
docker compose up --build
```

Frontend: http://localhost:8080  
Backend docs: http://localhost:8000/docs

Optional health checks:

```bash
curl http://localhost:8000/health/
curl http://localhost:8000/health/openrouter
```

### Run without Docker (local dev)

```bash
cd superq-chat
cp env/.env.example .env
# Edit .env and set your OPENROUTER_API_KEY (required)
# Configure models via MODELS JSON (see .env.example)
# Set DEFAULT_CHAT_MODEL_ALIAS to one alias from MODELS
```

```bash
# Install all dependencies (including dev/test)
uv sync --extra dev
```

### Run backend (local dev)

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

### Verify your API key

```bash
curl http://localhost:8000/health/openrouter
# {"status":"ok","message":"OpenRouter key is valid"}
```

## Frontend (React + Vite, local dev)

Located under `frontend/`.

```bash
cd frontend
npm install
npm run dev
```

The dev server runs on http://localhost:5173 and talks to the FastAPI backend at http://localhost:8000.

## Tests

```bash
uv sync --extra dev   # if not done already
uv run pytest -v
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENROUTER_API_KEY` | Yes | — | Your OpenRouter API key |
| `MODELS` | Yes | — | JSON object mapping alias to `"provider/model"` (e.g. `{"primary":"openrouter/openai/gpt-4o-mini","quality":"openrouter/anthropic/claude-3.5-sonnet"}`). App startup fails if missing. |
| `DEFAULT_CHAT_MODEL_ALIAS` | No | first configured alias | Default alias when neither request nor thread specifies model. If set, it must exist in `MODELS`. |
| `LLM_PROVIDER_BACKEND` | No | `openrouter` | Selects provider wiring from config. This pass supports `openrouter` only. |
| `CACHE_BACKEND` | No | `inmemory` | Selects cache/queue backend from config. This pass supports `inmemory` only. |
| `CACHE_TTL_SECONDS` | No | `300` | TTL in seconds for cached model responses. Must be greater than 0. |
| `OPENROUTER_BASE_URL` | No | `https://openrouter.ai/api/v1` | OpenRouter API base URL used by the provider adapter. |
| `OPENROUTER_TIMEOUT_SECONDS` | No | `30.0` | Request timeout in seconds for OpenRouter calls. Must be greater than 0. |
| `DATABASE_URL` | No | `sqlite:///./app.db` | SQLAlchemy database URL |

Container wiring is now config-driven for provider and cache selection; unsupported values fail fast at startup with explicit validation errors.

## API Reference

All endpoints are also available interactively at `/docs` (Swagger UI).

### Health / Discovery

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health/` | Basic health check |
| GET | `/health/openrouter` | Verify OpenRouter API key |
| GET | `/health/models` | List available model aliases (used by frontend dropdown) |

### Threads

| Method | Path | Description |
|--------|------|-------------|
| POST | `/threads` | Create a new chat thread |
| GET | `/threads` | List all threads (supports `offset`, `limit`) |
| GET | `/threads/{id}` | Retrieve a single thread |

### Messages

| Method | Path | Description |
|--------|------|-------------|
| POST | `/threads/{id}/messages` | Post a user message and get an LLM reply |
| GET | `/threads/{id}/messages` | Retrieve message history (supports `limit`, `since_id`) |

### Summaries

| Method | Path | Description |
|--------|------|-------------|
| GET | `/threads/{id}/summaries` | List all summaries (local + global) |
| POST | `/threads/{id}/summaries/refresh` | Trigger summarization manually |

### Request / Response Schemas

**POST /threads**

```json
{
  "system_prompt": "You are a helpful coding assistant.",
  "title": "My project chat",
  "initial_model": "primary"
}
```

Response (201):

```json
{
  "id": 1,
  "title": "My project chat",
  "system_prompt": "You are a helpful coding assistant.",
  "current_model": "primary",
  "created_at": "2026-03-04T12:00:00Z",
  "updated_at": "2026-03-04T12:00:00Z"
}
```

**POST /threads/{id}/messages**

```json
{
  "content": "Explain async/await in Python",
  "sender": "user",
  "model": "primary"
}
```

`model` is optional: any alias from `GET /health/models` (e.g. `"primary"`, `"quality"`), or omit for the thread default.

Response (201):

```json
{
  "user_message": {
    "id": 1, "thread_id": 1, "role": "user",
    "sender": "user", "content": "Explain async/await in Python",
    "model_id": null, "created_at": "2026-03-04T12:00:01Z"
  },
  "assistant_message": {
    "id": 2, "thread_id": 1, "role": "assistant",
    "sender": "agent", "content": "async/await allows you to ...",
    "model_id": "openai/gpt-3.5-turbo", "created_at": "2026-03-04T12:00:02Z"
  },
  "model_used": "openai/gpt-3.5-turbo"
}
```

## Sample Interactions

### 1. Create a thread

```bash
curl -X POST http://localhost:8000/threads \
  -H "Content-Type: application/json" \
  -d '{"system_prompt": "You are a helpful coding assistant.", "title": "Python help"}'
```

### 2. Send a message (primary model)

```bash
curl -X POST http://localhost:8000/threads/1/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "What is a decorator in Python?", "sender": "user", "model": "primary"}'
```

### 3. Switch to quality model mid-conversation

```bash
curl -X POST http://localhost:8000/threads/1/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "Now explain it differently", "sender": "user", "model": "quality"}'
```

### 4. Retrieve message history

```bash
curl http://localhost:8000/threads/1/messages?limit=50
```

### 5. Retrieve auto-summaries

```bash
curl http://localhost:8000/threads/1/summaries
```

Example summary response:

```json
[
  {
    "id": 1,
    "thread_id": 1,
    "level": 1,
    "summary_text": "User asked about Python decorators. Assistant explained that decorators are functions that modify the behavior of other functions...",
    "covers_up_to_message_id": 20,
    "created_at": "2026-03-04T12:05:00Z"
  },
  {
    "id": 2,
    "thread_id": 1,
    "level": 2,
    "summary_text": "Conversation covers Python fundamentals: decorators, async/await, and type hints. User is building a web service.",
    "covers_up_to_message_id": 20,
    "created_at": "2026-03-04T12:05:01Z"
  }
]
```

## Key Features

- Thread creation and listing with persistent system prompt
- **Provider-agnostic LLM layer**: `LLMProvider` Protocol — add new providers (Ollama, direct OpenAI, etc.) with a single class
- **Model catalog + routing policy split**: alias data and selection policy can evolve independently
- **ServiceContainer + ThreadChatService**: composition and use-case orchestration are decoupled from routes
- Multi-model support switchable per message; frontend model dropdown populated from `GET /health/models`
- Hierarchical auto-summarization:
  - **Level 1 (local):** chunk summaries after every N messages
  - **Level 2 (global):** high-level summary after M local summaries
- Context building that combines system prompt, summaries, and recent messages
- Request-fingerprint based cache + request coalescing (swappable via `CacheQueueBackend` protocol)
- Dedicated summarization model support (optional)
- OpenRouter key verification endpoint (`GET /health/openrouter`)
