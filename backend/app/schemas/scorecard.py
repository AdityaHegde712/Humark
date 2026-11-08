"""Pydantic schemas for benchmark scorecard telemetry and model comparisons."""

from __future__ import annotations

import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.percentile import PercentileBenchmark
from app.core.stats import WilsonInterval


class PercentileBenchmarkResponse(PercentileBenchmark):
    """Percentile benchmark response schema for API clients."""

    pass


class ModelComparisonItem(BaseModel):
    """Head-to-head comparison between human participant and a baseline model."""

    model_config = ConfigDict(from_attributes=True)

    model_name: str = Field(description="Identifier of the evaluated model")
    model_accuracy: float = Field(
        description="Model accuracy on the exact same challenges attempted by user"
    )
    user_beat_model: int = Field(
        description="Count of challenges where user was correct and model was incorrect"
    )
    model_beat_user: int = Field(
        description="Count of challenges where model was correct and user was incorrect"
    )
    ties: int = Field(
        description="Count of challenges where both were correct or both incorrect"
    )
    accuracy_delta: float = Field(
        description="Accuracy advantage of user over model (user_accuracy - model_accuracy)"
    )
    verdict: Literal["ahead", "behind", "tied"] = Field(
        description="User positioning relative to model: ahead, behind, or tied"
    )


class CategoryBreakdownItem(BaseModel):
    """Performance breakdown for a challenge category or design tag."""

    model_config = ConfigDict(from_attributes=True)

    category: str = Field(description="Challenge category or tag")
    total_attempts: int = Field(description="Total attempts in this category")
    correct_attempts: int = Field(description="Correct attempts in this category")
    accuracy: float = Field(description="Accuracy in this category")


class VerificationAuditSummary(BaseModel):
    """Summary of tamper-evident verification audit receipt."""

    model_config = ConfigDict(from_attributes=True)

    verification_hash: str = Field(
        description="Deterministic SHA-256 digest of verified session attempts"
    )
    completed_at: datetime.datetime = Field(
        description="Timestamp when verification was finalized"
    )
    cumulative_accuracy: float = Field(
        description="Cumulative accuracy across all verification rounds"
    )
    round_1_correct: int = Field(description="Correct attempts in Round 1")
    round_2_correct: int = Field(description="Correct attempts in Round 2")
    round_3_correct: int = Field(description="Correct attempts in Round 3")


class ScorecardResponse(BaseModel):
    """Comprehensive performance scorecard for a Humark benchmark session."""

    model_config = ConfigDict(from_attributes=True)

    session_id: str = Field(description="Unique session identifier")
    total_attempts: int = Field(description="Total attempts submitted in session")
    correct_attempts: int = Field(description="Total correct attempts")
    accuracy: float = Field(description="Raw accuracy ratio (correct / total)")
    wilson_interval: WilsonInterval = Field(
        description="Wilson score 95% confidence interval and sample size warning"
    )
    percentile_benchmark: PercentileBenchmarkResponse | None = Field(
        default=None,
        description="Human population percentile ranking and bell curve telemetry",
    )
    average_time_taken_ms: float = Field(
        description="Mean decision latency in milliseconds"
    )
    current_round: int = Field(description="Current active round number")
    rounds_completed: int = Field(description="Number of completed 10-item rounds")
    status: str = Field(description="Current session status")
    is_verified: bool = Field(
        description="True if benchmark session meets verification threshold"
    )
    model_comparisons: list[ModelComparisonItem] = Field(
        default_factory=list,
        description="Head-to-head comparison records against baseline models",
    )
    category_breakdown: list[CategoryBreakdownItem] = Field(
        default_factory=list,
        description="Accuracy metrics aggregated by challenge category",
    )
    verification_audit: VerificationAuditSummary | None = Field(
        default=None,
        description="Audit receipt if session completed verification evaluation",
    )
    verification_hash: str | None = Field(
        default=None,
        description="Tamper-evident verification digest if verified or completed",
    )
