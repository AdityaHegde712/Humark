"""Pydantic schemas for session lifecycle, challenge requests, and attempt receipts."""

import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GameSessionResponse(BaseModel):
    """Schema representing game session state and progress."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    current_round: int
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    total_attempts: int = 0
    correct_attempts: int = 0
    round_attempts: int = 0
    accuracy: float = 0.0


class AttemptCreate(BaseModel):
    """Schema for submitting an attempt on a challenge."""

    selected_variant: str = Field(
        ...,
        description="User choice of variant ('A' or 'B')",
    )
    time_taken_ms: int = Field(
        ...,
        ge=0,
        description="Decision latency in milliseconds",
    )

    @field_validator("selected_variant")
    @classmethod
    def validate_variant(cls, v: str) -> str:
        upper = v.strip().upper()
        if upper not in ("A", "B"):
            raise ValueError("selected_variant must be 'A' or 'B'")
        return upper


class ModelComparisonResult(BaseModel):
    """Baseline model prediction with comparison against ground truth."""

    model_config = ConfigDict(from_attributes=True)

    model_name: str
    model_version: str
    predicted_variant: str
    confidence: float
    reasoning: str
    prompt_version: str
    token_count: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    is_model_correct: bool


class AttemptReceipt(BaseModel):
    """Rich receipt revealed immediately after an attempt is submitted."""

    model_config = ConfigDict(from_attributes=True)

    attempt_id: str
    session_id: str
    challenge_id: str
    round_number: int
    attempt_index: int
    round_items: int = 10
    selected_variant: str
    is_correct: bool
    time_taken_ms: int

    # Ground truth data revealed post-decision
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

    # Attached model predictions with accuracy flag
    model_predictions: list[ModelComparisonResult] = []


class NextChallengeResponse(BaseModel):
    """Response returned when requesting next challenge in session."""

    model_config = ConfigDict(from_attributes=True)

    id: str | None = None
    title: str | None = None
    category: str | None = None
    thumbnail_a_url: str | None = None
    thumbnail_b_url: str | None = None
    round_completed: bool = False
    round_number: int
    attempt_index: int = 0
    total_round_items: int = 10
