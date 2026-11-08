"""SQLAlchemy data models for challenges and model predictions."""

import datetime
import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Challenge(Base):
    """Challenge ground truth representing a statistically significant A/B test."""

    __tablename__ = "challenges"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(
        String(64),
        default="youtube_thumbnails",
        nullable=False,
        index=True,
    )
    primary_motif: Mapped[str] = mapped_column(
        String(64),
        default="visual_contrast",
        nullable=False,
    )
    thumbnail_a_url: Mapped[str] = mapped_column(String(512), nullable=False)
    thumbnail_b_url: Mapped[str] = mapped_column(String(512), nullable=False)

    # Variant A metrics
    impressions_a: Mapped[int] = mapped_column(Integer, nullable=False)
    clicks_a: Mapped[int] = mapped_column(Integer, nullable=False)
    ctr_a: Mapped[float] = mapped_column(Float, nullable=False)

    # Variant B metrics
    impressions_b: Mapped[int] = mapped_column(Integer, nullable=False)
    clicks_b: Mapped[int] = mapped_column(Integer, nullable=False)
    ctr_b: Mapped[float] = mapped_column(Float, nullable=False)

    # Statistical outcomes
    winning_variant: Mapped[str] = mapped_column(
        String(1), nullable=False
    )  # "A" or "B"
    z_score: Mapped[float] = mapped_column(Float, nullable=False)
    p_value: Mapped[float] = mapped_column(Float, nullable=False)

    # Provenance and metadata
    provenance_source: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Attached model predictions
    predictions: Mapped[list["ModelPrediction"]] = relationship(
        "ModelPrediction",
        back_populates="challenge",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ModelPrediction(Base):
    """Pre-computed or live evaluation result from a multimodal model."""

    __tablename__ = "model_predictions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    challenge_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("challenges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    predicted_variant: Mapped[str] = mapped_column(
        String(1), nullable=False
    )  # "A" or "B"
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    challenge: Mapped["Challenge"] = relationship(
        "Challenge", back_populates="predictions"
    )
