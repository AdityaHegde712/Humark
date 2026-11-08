"""SQLAlchemy data models for gameplay sessions and challenge attempts."""

import datetime
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.challenge import Challenge
    from app.models.verification import VerificationAuditLog


class GameSession(Base):
    """Represents a human benchmark session progressing through rounds."""

    __tablename__ = "game_sessions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    current_round: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="active",
        nullable=False,
    )  # "active", "round_completed", "verified", "failed"
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Attempts recorded during this session
    attempts: Mapped[list["SessionAttempt"]] = relationship(
        "SessionAttempt",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Verification audit log (if verified or evaluated)
    verification_audit: Mapped["VerificationAuditLog | None"] = relationship(
        "VerificationAuditLog",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SessionAttempt(Base):
    """Represents an individual user submission on a specific challenge."""

    __tablename__ = "session_attempts"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "challenge_id",
            name="uq_session_challenge",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    challenge_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("challenges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    round_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    selected_variant: Mapped[str] = mapped_column(
        String(1),
        nullable=False,
    )  # "A" or "B"
    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    time_taken_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    session: Mapped["GameSession"] = relationship(
        "GameSession",
        back_populates="attempts",
    )
    challenge: Mapped["Challenge"] = relationship(
        "Challenge",
        lazy="selectin",
    )
