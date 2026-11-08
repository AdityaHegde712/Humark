"""SQLAlchemy data model for verification audit records and tamper-evident logs."""

import datetime
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.session import GameSession


class VerificationAuditLog(Base):
    """Tamper-evident audit record for 3-round benchmark verification."""

    __tablename__ = "verification_audit_logs"

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
        unique=True,
        index=True,
    )
    completed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    total_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    correct_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    cumulative_accuracy: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    round_1_correct: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    round_2_correct: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    round_3_correct: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    verification_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    session: Mapped["GameSession"] = relationship(
        "GameSession",
        back_populates="verification_audit",
    )
