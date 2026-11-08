"""Database engine and session management.

Supports both PostgreSQL and SQLite (in-memory or file-based for testing).
"""

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base


def get_database_url() -> str:
    """Resolve database URL from environment with fallback to local SQLite."""
    sync_url = os.getenv("SYNC_DATABASE_URL")
    if sync_url:
        return sync_url

    raw_url = os.getenv("DATABASE_URL")
    if raw_url:
        # Convert async driver string to standard sync driver if necessary
        if raw_url.startswith("postgresql+asyncpg://"):
            return raw_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        return raw_url

    return "sqlite:///./humark.db"


database_url = get_database_url()
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}

engine = create_engine(
    database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def init_db(target_engine=None) -> None:
    """Initialize database tables."""
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
