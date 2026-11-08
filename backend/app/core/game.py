"""Game engine core service managing sessions, unseen challenge selection, and attempt grading."""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.challenge import Challenge, ModelPrediction
from app.models.session import GameSession, SessionAttempt
from app.schemas.challenge import ChallengePublic
from app.schemas.session import (
    AttemptReceipt,
    ModelComparisonResult,
)

ITEMS_PER_ROUND = 10
MAX_ROUNDS = 3


class GameEngineError(Exception):
    """Base exception for game engine operations."""

    pass


class SessionNotFoundError(GameEngineError):
    """Raised when the specified session cannot be found."""

    pass


class ChallengeNotFoundError(GameEngineError):
    """Raised when the specified challenge is missing or inactive."""

    pass


class DuplicateAttemptError(GameEngineError):
    """Raised when an attempt is submitted for an already answered challenge."""

    pass


class RoundCompletedError(GameEngineError):
    """Raised when attempting to submit answers after round quota is reached."""

    pass


def create_new_session(db: Session) -> GameSession:
    """Unconditionally create and persist a fresh game session."""
    new_session = GameSession(
        id=str(uuid.uuid4()),
        current_round=1,
        status="active",
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


def get_or_create_session(
    db: Session,
    session_id: str | None = None,
) -> GameSession:
    """Retrieve an existing game session or create a new guest session."""
    if session_id:
        existing = db.query(GameSession).filter(GameSession.id == session_id).first()
        if existing:
            return existing

    return create_new_session(db)


def get_session_stats(db: Session, session_id: str) -> dict:
    """Calculate aggregate gameplay telemetry for the active session."""
    session = db.query(GameSession).filter(GameSession.id == session_id).first()
    if not session:
        raise SessionNotFoundError(f"Session '{session_id}' not found")

    attempts = session.attempts or []
    total_attempts = len(attempts)
    correct_attempts = sum(1 for a in attempts if a.is_correct)
    round_attempts = sum(
        1 for a in attempts if a.round_number == session.current_round
    )
    accuracy = (
        round(correct_attempts / total_attempts * 100.0, 2)
        if total_attempts > 0
        else 0.0
    )

    return {
        "id": session.id,
        "current_round": session.current_round,
        "status": session.status,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "total_attempts": total_attempts,
        "correct_attempts": correct_attempts,
        "round_attempts": round_attempts,
        "accuracy": accuracy,
    }


def get_next_unseen_challenge(
    db: Session,
    session_id: str,
) -> ChallengePublic | None:
    """Select the next active challenge that this session has not yet attempted.

    Enforces 10 items per round. Returns None when round threshold is reached
    or when no unseen challenges remain.
    """
    session = get_or_create_session(db, session_id)

    # Check how many items were attempted in current round
    round_attempts_count = (
        db.query(SessionAttempt)
        .filter(
            SessionAttempt.session_id == session.id,
            SessionAttempt.round_number == session.current_round,
        )
        .count()
    )

    if round_attempts_count >= ITEMS_PER_ROUND:
        if session.status == "active":
            session.status = "round_completed"
            db.commit()
            db.refresh(session)
        return None

    # Subquery for all challenges ever attempted in this session
    attempted_challenge_ids = (
        select(SessionAttempt.challenge_id)
        .where(SessionAttempt.session_id == session.id)
    )

    challenge = (
        db.query(Challenge)
        .filter(
            Challenge.is_active.is_(True),
            ~Challenge.id.in_(attempted_challenge_ids),
        )
        .order_by(Challenge.id.asc())
        .first()
    )

    if not challenge:
        return None

    return ChallengePublic.model_validate(challenge)


def record_attempt(
    db: Session,
    session_id: str,
    challenge_id: str,
    selected_variant: str,
    time_taken_ms: int,
) -> AttemptReceipt:
    """Record user variant decision, grade correctness, and produce receipt."""
    session = db.query(GameSession).filter(GameSession.id == session_id).first()
    if not session:
        raise SessionNotFoundError(f"Session '{session_id}' not found")

    variant = selected_variant.strip().upper()
    if variant not in ("A", "B"):
        raise ValueError("selected_variant must be 'A' or 'B'")

    # Check for duplicate attempt
    existing_attempt = (
        db.query(SessionAttempt)
        .filter(
            SessionAttempt.session_id == session.id,
            SessionAttempt.challenge_id == challenge_id,
        )
        .first()
    )
    if existing_attempt:
        raise DuplicateAttemptError(
            f"Challenge '{challenge_id}' has already been attempted in session '{session.id}'"
        )

    # Check round attempt limit
    round_attempts_count = (
        db.query(SessionAttempt)
        .filter(
            SessionAttempt.session_id == session.id,
            SessionAttempt.round_number == session.current_round,
        )
        .count()
    )

    if round_attempts_count >= ITEMS_PER_ROUND:
        if session.status == "active":
            session.status = "round_completed"
            db.commit()
        raise RoundCompletedError(
            f"Round {session.current_round} reached limit of {ITEMS_PER_ROUND} items"
        )

    # Fetch target challenge
    challenge = (
        db.query(Challenge)
        .filter(Challenge.id == challenge_id, Challenge.is_active.is_(True))
        .first()
    )
    if not challenge:
        raise ChallengeNotFoundError(
            f"Active challenge '{challenge_id}' does not exist"
        )

    is_correct = variant == challenge.winning_variant.upper()
    attempt = SessionAttempt(
        id=str(uuid.uuid4()),
        session_id=session.id,
        challenge_id=challenge.id,
        round_number=session.current_round,
        selected_variant=variant,
        is_correct=is_correct,
        time_taken_ms=time_taken_ms,
    )

    try:
        db.add(attempt)
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateAttemptError(
            f"Challenge '{challenge_id}' has already been attempted"
        ) from exc

    attempt_index = round_attempts_count + 1
    if attempt_index >= ITEMS_PER_ROUND:
        session.status = "round_completed"

    db.commit()
    db.refresh(attempt)
    db.refresh(session)

    # Pre-computed model predictions
    predictions = (
        db.query(ModelPrediction)
        .filter(ModelPrediction.challenge_id == challenge.id)
        .order_by(ModelPrediction.created_at.asc())
        .all()
    )

    model_comparisons = [
        ModelComparisonResult(
            model_name=p.model_name,
            model_version=p.model_version,
            predicted_variant=p.predicted_variant,
            confidence=p.confidence,
            reasoning=p.reasoning,
            prompt_version=p.prompt_version,
            token_count=p.token_count,
            latency_ms=p.latency_ms,
            cost_usd=p.cost_usd,
            is_model_correct=(
                p.predicted_variant.upper() == challenge.winning_variant.upper()
            ),
        )
        for p in predictions
    ]

    return AttemptReceipt(
        attempt_id=attempt.id,
        session_id=session.id,
        challenge_id=challenge.id,
        round_number=attempt.round_number,
        attempt_index=attempt_index,
        round_items=ITEMS_PER_ROUND,
        selected_variant=attempt.selected_variant,
        is_correct=attempt.is_correct,
        time_taken_ms=attempt.time_taken_ms,
        title=challenge.title,
        category=challenge.category,
        thumbnail_a_url=challenge.thumbnail_a_url,
        thumbnail_b_url=challenge.thumbnail_b_url,
        impressions_a=challenge.impressions_a,
        clicks_a=challenge.clicks_a,
        ctr_a=challenge.ctr_a,
        impressions_b=challenge.impressions_b,
        clicks_b=challenge.clicks_b,
        ctr_b=challenge.ctr_b,
        winning_variant=challenge.winning_variant,
        z_score=challenge.z_score,
        p_value=challenge.p_value,
        provenance_source=challenge.provenance_source,
        model_predictions=model_comparisons,
    )
