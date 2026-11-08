"""Pydantic schemas for verification state machine, receipts, and round progression."""

import datetime
from pydantic import BaseModel, ConfigDict, Field


class RoundAdvanceResponse(BaseModel):
    """Response returned when successfully advancing to the next round."""

    session_id: str = Field(description="Unique session identifier")
    current_round: int = Field(description="New active round number (1, 2, or 3)")
    status: str = Field(description="Session status (e.g. active)")
    message: str = Field(description="Informational status message")


class VerificationResult(BaseModel):
    """Verification outcome and tamper-evident audit record."""

    model_config = ConfigDict(from_attributes=True)

    session_id: str = Field(description="Unique session identifier")
    completed_at: datetime.datetime = Field(
        description="Timestamp when evaluation was finalized"
    )
    total_attempts: int = Field(description="Total completed attempts (30)")
    correct_attempts: int = Field(description="Total correct attempts")
    cumulative_accuracy: float = Field(
        description="Percentage of correct attempts across all rounds"
    )
    is_verified: bool = Field(
        description="True strictly if cumulative accuracy > 70% (>= 22/30)"
    )
    round_1_correct: int = Field(description="Correct attempts in Round 1")
    round_2_correct: int = Field(description="Correct attempts in Round 2")
    round_3_correct: int = Field(description="Correct attempts in Round 3")
    verification_hash: str = Field(
        description="SHA-256 tamper-evident digest of session attempts"
    )


class VerificationStatusResponse(BaseModel):
    """Current progression status across the 3-round verification track."""

    model_config = ConfigDict(from_attributes=True)

    session_id: str = Field(description="Unique session identifier")
    current_round: int = Field(description="Current round number (1, 2, or 3)")
    status: str = Field(description="Current session status")
    round_attempts: int = Field(
        description="Number of attempts completed in current round"
    )
    total_attempts: int = Field(
        description="Total attempts completed across all rounds"
    )
    is_completed: bool = Field(
        description="True if all 3 rounds (30 items) are completed"
    )
    is_verified: bool | None = Field(
        default=None,
        description="True if verified, False if failed, None if incomplete",
    )
    cumulative_accuracy: float | None = Field(
        default=None,
        description="Cumulative accuracy percentage",
    )
    round_scores: dict[str, int] = Field(
        default_factory=dict,
        description="Correct count per round (round_1, round_2, round_3)",
    )
    verification_hash: str | None = Field(
        default=None,
        description="Tamper-evident verification hash if evaluated",
    )
    audit_log: VerificationResult | None = Field(
        default=None,
        description="Full audit log record if completed",
    )
