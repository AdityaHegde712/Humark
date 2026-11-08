"""Humark FastAPI Application Entrypoint."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app.api.admin import router as admin_router
from app.api.challenges import router as challenges_router
from app.api.scorecard import router as scorecard_router
from app.api.sessions import router as sessions_router
from app.api.verification import router as verification_router
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown."""
    init_db()
    if os.getenv("AUTO_SEED", "true").lower() in ("true", "1", "yes"):
        try:
            from app.scripts.seed import auto_seed_if_empty

            auto_seed_if_empty()
        except Exception as exc:
            import logging

            logging.getLogger("humark").warning(f"Auto-seed check failed: {exc}")
    yield


app = FastAPI(
    title="Humark API",
    description="Human vs AI YouTube Thumbnail Benchmark Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Parse CORS origins from environment or default to local Vite dev server
cors_origins_env = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
allowed_origins: list[str] = [
    origin.strip() for origin in cors_origins_env.split(",") if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory for thumbnails
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include API routers
app.include_router(admin_router)
app.include_router(challenges_router)
app.include_router(sessions_router)
app.include_router(verification_router)
app.include_router(scorecard_router)


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """Return health status of Humark API."""
    return {
        "status": "ok",
        "service": "humark-api",
    }
