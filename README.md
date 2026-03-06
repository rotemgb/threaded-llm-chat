# threaded-llm-chat

Multi-model chat threading service with hierarchical summaries, built with **FastAPI**, **SQLAlchemy**, **OpenRouter**, and a **React** frontend.

---

## Quick start

```bash
git clone <repo-url>
cd threaded-llm-chat
cp env/.env.example .env
# Edit .env and set OPENROUTER_API_KEY (required)
docker compose up --build
```

- **Frontend:** http://localhost:8080  
- **API docs:** http://localhost:8000/docs  

---

## What this does

- **Threads** with a persistent system prompt and per-message model choice (e.g. `primary` vs `quality`).
- **Bounded context**: system prompt + latest global summary + recent local summaries + recent messages, so long threads stay within the LLM context window.
- **Hierarchical summarization**: Level 1 (local) every 10 messages, Level 2 (global) every 3 locals; runs in the background so chat stays fast.
- **Optional LLMOps**: in-memory TTL cache and in-flight request coalescing for identical LLM requests.

<img src="docs/screenshots/01-thread-creation.png" alt="Thread creation Model Selection Dropdwon" width="900">

*Creating a new chat thread and model selection dropdown.*

---

## Architecture

![Architecture flow](docs/architecture-flow.png)

High-level components:

```
Browser (React :5173 dev / :8080 Docker)
  │
  ▼
FastAPI backend (:8000)
  ├── ServiceContainer   — dependency composition at startup (app.state)
  ├── ThreadChatService  — orchestrates message flow, context, LLM, persistence
  ├── ContextService     — builds message list (system + summaries + recent messages)
  ├── LLMRouter          — model alias → ModelCatalog → provider; CacheQueue in front
  │     └── LLMProvider protocol (OpenRouterProvider; extensible)
  ├── SummaryWorker      — async job, own UoW; calls SummaryService + LLMRouter
  ├── SummaryService     — Level 1 / Level 2 summarization
  ├── SqlAlchemyUnitOfWork — thread, message, summary repos
  └── SQLite (SQLAlchemy ORM)
```

## Backend (FastAPI + uv)

- **Python 3.12** · Dependency management via [uv](https://docs.astral.sh/uv/) and `pyproject.toml`
- **App layout:** FastAPI app in `app/`; SQLite + SQLAlchemy in `app/db/`; domain services in `app/domain/services/`; OpenRouter + model registry in `app/integration/`
- **LLM layer:** `LLMProvider` Protocol in `app/integration/llm_provider.py`; OpenRouter in `app/integration/openrouter/`; model catalog + routing in `app/integration/model_registry.py`
- **Orchestration:** `ServiceContainer` in `app/core/container.py`; `ThreadChatService` in `app/domain/services/thread_chat_service.py`; context and summarization in `app/domain/services/`

### Run with Docker

From the project root:

```bash
cp env/.env.example .env
# Edit .env and set OPENROUTER_API_KEY (required)
docker compose up --build
```

- Frontend: http://localhost:8080  
- API docs: http://localhost:8000/docs  

Health checks:

```bash
curl http://localhost:8000/health/
curl http://localhost:8000/health/openrouter
```

### Run locally (development)

1. Install [uv](https://docs.astral.sh/uv/) if needed.
2. From the project root:

```bash
cp env/.env.example .env
# Edit .env: set OPENROUTER_API_KEY; optionally adjust MODELS and DEFAULT_CHAT_MODEL_ALIAS
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs  
- Verify OpenRouter: `curl http://localhost:8000/health/openrouter`

## Frontend (React + Vite)

Located under `frontend/`. For local dev with the backend on port 8000:

```bash
cd frontend
npm install
npm run dev
```

- Dev server: http://localhost:5173 (proxies API to backend)
- Default backend: `http://localhost:8000`; override with `VITE_API_BASE_URL` in `.env` if needed

<img src="docs/screenshots/02-model-switch.jpg" alt="Model switching mid-conversation" width="600">

*Switching between models (e.g. default → primary → quality) mid-thread via the model dropdown without interrupting conversation memory.*

## Tests

```bash
uv sync --extra dev   # if not done already
uv run pytest -v
```

Test suite covers health endpoints, full thread/message flow, and swappability boundaries (e.g. in-memory vs mocked providers).

## Project structure

```
threaded-llm-chat/
├── app/
│   ├── api/routes/       # FastAPI route handlers (health, threads, messages, summaries)
│   ├── core/             # Config, ServiceContainer, dependencies
│   ├── db/               # SQLAlchemy models, UoW, repositories
│   ├── domain/services/  # ThreadChatService, ContextService, SummaryService, LLMRouter, SummaryWorker
│   ├── integration/      # LLM provider protocol, OpenRouter client, model registry, cache queue
│   └── schemas/          # Pydantic request/response models
├── frontend/             # React + Vite app
├── env/.env.example      # Example environment variables
├── docs/                 # Presentation, architecture diagram
└── tests/                # Pytest tests
```

## Documentation

- **API:** Interactive OpenAPI docs at http://localhost:8000/docs when the backend is running
- **Architecture:** Diagram at [docs/architecture-flow.png](docs/architecture-flow.png)
- **Presentation:** [docs/presentation.md](docs/presentation.md) (Marp deck; export to PDF with `npx @marp-team/marp-cli docs/presentation.md --pdf`)

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

<img src="docs/screenshots/03-summaries.png" alt="Summary panel showing local and global summaries" width="600">

*The summary panel displays Level 1 (local) and Level 2 (global) summaries as the conversation grows.*

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
- Dedicated summarization model support
- OpenRouter key verification endpoint (`GET /health/openrouter`)
