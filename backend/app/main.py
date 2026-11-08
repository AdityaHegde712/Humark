"""Humark FastAPI Application Entrypoint."""

import os
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Humark API",
    description="Human vs AI YouTube Thumbnail Benchmark Platform",
    version="0.1.0",
)

# Parse CORS origins from environment or default to local Vite dev server
cors_origins_env = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
allowed_origins: List[str] = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """Return health status of Humark API."""
    return {
        "status": "ok",
        "service": "humark-api",
    }
