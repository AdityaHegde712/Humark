"""Database engine and session management.

Supports both PostgreSQL and SQLite (in-memory or file-based for testing).
"""

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
import app.models  # noqa: F401


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
    # Lightweight migration for existing SQLite databases
    try:
        from sqlalchemy import text

        with eng.connect() as conn:
            conn.execute(
                text(
                    "ALTER TABLE challenges ADD COLUMN primary_motif VARCHAR(64) DEFAULT 'visual_contrast'"
                )
            )
            conn.commit()
    except Exception:
        # Column already exists or dialect does not require alter
        pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
