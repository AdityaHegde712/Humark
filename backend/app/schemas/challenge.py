"""Pydantic schemas for challenge ingestion, gameplay exposure, and post-answer receipts."""

import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelPredictionSchema(BaseModel):
    """Schema representing model evaluation response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    model_name: str
    model_version: str
    predicted_variant: str
    confidence: float
    reasoning: str
    prompt_version: str
    token_count: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    created_at: datetime.datetime | None = None


class ChallengeCreate(BaseModel):
    """Schema for ingesting raw challenge A/B test data."""

    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    title: str = Field(..., min_length=3, max_length=255)
    category: str = Field(default="youtube_thumbnails", max_length=64)
    thumbnail_a_url: str = Field(..., min_length=1, max_length=512)
    thumbnail_b_url: str = Field(..., min_length=1, max_length=512)
    impressions_a: int = Field(..., ge=0)
    clicks_a: int = Field(..., ge=0)
    impressions_b: int = Field(..., ge=0)
    clicks_b: int = Field(..., ge=0)
    provenance_source: str = Field(..., min_length=1, max_length=255)

    @field_validator("clicks_a")
    @classmethod
    def validate_clicks_a(cls, v: int, info) -> int:
        impressions = info.data.get("impressions_a")
        if impressions is not None and v > impressions:
            raise ValueError(
                f"clicks_a ({v}) cannot exceed impressions_a ({impressions})"
            )
        return v

    @field_validator("clicks_b")
    @classmethod
    def validate_clicks_b(cls, v: int, info) -> int:
        impressions = info.data.get("impressions_b")
        if impressions is not None and v > impressions:
            raise ValueError(
                f"clicks_b ({v}) cannot exceed impressions_b ({impressions})"
            )
        return v

    @field_validator("provenance_source")
    @classmethod
    def validate_provenance(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("provenance_source must not be blank")
        return stripped


# Alias for backward compatibility / ingestion clarity
ChallengeIngestionItem = ChallengeCreate


class ChallengePublic(BaseModel):
    """Public challenge schema for game play.

    STRICTLY HIDES: impressions, clicks, CTRs, winning variant, z_score, p_value!
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    category: str
    thumbnail_a_url: str
    thumbnail_b_url: str


class ChallengeReceipt(BaseModel):
    """Challenge receipt revealed AFTER an attempt has been made.

    Exposes complete ground truth and baseline model predictions.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    category: str
    thumbnail_a_url: str
    thumbnail_b_url: str
    impressions_a: int
    clicks_a: int
    ctr_a: float
    impressions_b: int
    clicks_b: int
    ctr_b: float
    winning_variant: str
    z_score: float
    p_value: float
    provenance_source: str
    predictions: list[ModelPredictionSchema] = []


class IngestionSummary(BaseModel):
    """Summary of batch ingestion execution."""

    total_submitted: int
    ingested_count: int
    rejected_count: int
    ingested_ids: list[str] = []
    rejections: list[dict[str, Any]] = []


class IngestionRequest(BaseModel):
    """Batch ingestion request body."""

    challenges: list[ChallengeCreate]
