from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.routes import health, threads
from app.core.config import get_settings
from app.core.container import build_container
from app.db.base import SessionLocal, engine
from app.db.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    container = build_container(settings=settings, session_factory=SessionLocal)
    app.state.settings = settings
    app.state.container = container

    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="threaded-llm-chat: Multi-Agent Chat Threading Service",
        lifespan=lifespan,
    )

    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(threads.router, tags=["threads"])

    return app


app = create_app()


@app.get("/")
def root():
    return RedirectResponse(url="/docs")
