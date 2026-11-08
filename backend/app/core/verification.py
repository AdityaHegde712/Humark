"""Verification state machine, round progression, and tamper-evident audit logging."""

import datetime
import hashlib
import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models.session import GameSession, SessionAttempt
from app.models.verification import VerificationAuditLog
from app.schemas.verification import (
    VerificationResult,
    VerificationStatusResponse,
)

ITEMS_PER_ROUND = 10
MAX_ROUNDS = 3
TOTAL_ITEMS = 30
VERIFICATION_THRESHOLD_CORRECT = 22  # > 70% threshold (22/30 = 73.33%)


class VerificationError(Exception):
    """Base exception for verification and round operations."""

    pass


class SessionNotFoundError(VerificationError):
    """Raised when the specified session cannot be found."""

    pass


class IncompleteRoundError(VerificationError):
    """Raised when advancing a round before completing all required attempts."""

    pass


class MaxRoundsReachedError(VerificationError):
    """Raised when attempting to advance beyond the final benchmark round."""

    pass


class VerificationIncompleteError(VerificationError):
    """Raised when evaluating verification before completing all 30 benchmark items."""

    pass


def compute_verification_hash(
    session_id: str,
    attempts: Sequence[SessionAttempt],
) -> str:
    """Compute a deterministic SHA-256 digest of session attempts.

    The digest provides a tamper-evident receipt: modifying any attempt
    (variant, correctness, challenge ID, or round) invalidates the hash.
    """
    sorted_attempts = sorted(
        attempts,
        key=lambda a: (a.round_number, a.challenge_id),
    )
    lines = [f"HUMARK-VERIFY-V1:SESSION:{session_id}"]
    for a in sorted_attempts:
        line = (
            f"{a.round_number}|{a.challenge_id}|"
            f"{a.selected_variant}|{a.is_correct}|{a.time_taken_ms}"
        )
        lines.append(line)
    payload = "\n".join(lines)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def advance_round(db: Session, session_id: str) -> GameSession:
    """Advance the game session to the next round if current round is complete.

    Validates that exactly ITEMS_PER_ROUND (10) attempts have been made in current round.
    If current_round < MAX_ROUNDS (3), increments current_round and resets status to 'active'.
    If current_round == MAX_ROUNDS, raises MaxRoundsReachedError.
    """
    session = db.query(GameSession).filter(GameSession.id == session_id).first()
    if not session:
        raise SessionNotFoundError(f"Session '{session_id}' not found")

    round_attempts_count = (
        db.query(SessionAttempt)
        .filter(
            SessionAttempt.session_id == session.id,
            SessionAttempt.round_number == session.current_round,
        )
        .count()
    )

    if round_attempts_count < ITEMS_PER_ROUND:
        raise IncompleteRoundError(
            f"Round {session.current_round} is not complete "
            f"({round_attempts_count}/{ITEMS_PER_ROUND} attempts)"
        )

    if session.current_round >= MAX_ROUNDS:
        raise MaxRoundsReachedError(
            f"Cannot advance beyond Round {MAX_ROUNDS}; verification completed"
        )

    session.current_round += 1
    session.status = "active"
    db.commit()
    db.refresh(session)
    return session


def evaluate_verification(db: Session, session_id: str) -> VerificationResult:
    """Evaluate full 30-attempt verification benchmark and generate audit log.

    Enforces >70% accuracy threshold (>= 22/30 correct).
    Updates GameSession.status to 'verified' or 'failed'.
    Creates or updates the tamper-evident VerificationAuditLog.
    """
    session = db.query(GameSession).filter(GameSession.id == session_id).first()
    if not session:
        raise SessionNotFoundError(f"Session '{session_id}' not found")

    attempts = (
        db.query(SessionAttempt)
        .filter(SessionAttempt.session_id == session.id)
        .order_by(SessionAttempt.round_number.asc(), SessionAttempt.challenge_id.asc())
        .all()
    )

    if len(attempts) < TOTAL_ITEMS:
        raise VerificationIncompleteError(
            f"Verification requires {TOTAL_ITEMS} attempts, found {len(attempts)}"
        )

    round_1_correct = sum(
        1 for a in attempts if a.round_number == 1 and a.is_correct
    )
    round_2_correct = sum(
        1 for a in attempts if a.round_number == 2 and a.is_correct
    )
    round_3_correct = sum(
        1 for a in attempts if a.round_number == 3 and a.is_correct
    )
    total_correct = round_1_correct + round_2_correct + round_3_correct
    cumulative_accuracy = round(total_correct / len(attempts) * 100.0, 2)
    is_verified = total_correct >= VERIFICATION_THRESHOLD_CORRECT

    session.status = "verified" if is_verified else "failed"

    verification_hash = compute_verification_hash(session.id, attempts)
    now = datetime.datetime.now(datetime.timezone.utc)

    audit_log = (
        db.query(VerificationAuditLog)
        .filter(VerificationAuditLog.session_id == session.id)
        .first()
    )

    if audit_log:
        audit_log.completed_at = now
        audit_log.total_attempts = len(attempts)
        audit_log.correct_attempts = total_correct
        audit_log.cumulative_accuracy = cumulative_accuracy
        audit_log.is_verified = is_verified
        audit_log.round_1_correct = round_1_correct
        audit_log.round_2_correct = round_2_correct
        audit_log.round_3_correct = round_3_correct
        audit_log.verification_hash = verification_hash
    else:
        audit_log = VerificationAuditLog(
            id=str(uuid.uuid4()),
            session_id=session.id,
            completed_at=now,
            total_attempts=len(attempts),
            correct_attempts=total_correct,
            cumulative_accuracy=cumulative_accuracy,
            is_verified=is_verified,
            round_1_correct=round_1_correct,
            round_2_correct=round_2_correct,
            round_3_correct=round_3_correct,
            verification_hash=verification_hash,
        )
        db.add(audit_log)

    db.commit()
    db.refresh(session)
    db.refresh(audit_log)

    return VerificationResult.model_validate(audit_log)


def get_verification_status(
    db: Session,
    session_id: str,
) -> VerificationStatusResponse:
    """Return round progression status and verification audit breakdown."""
    session = db.query(GameSession).filter(GameSession.id == session_id).first()
    if not session:
        raise SessionNotFoundError(f"Session '{session_id}' not found")

    attempts = (
        db.query(SessionAttempt)
        .filter(SessionAttempt.session_id == session.id)
        .order_by(SessionAttempt.round_number.asc(), SessionAttempt.challenge_id.asc())
        .all()
    )

    total_attempts = len(attempts)
    round_attempts_count = sum(
        1 for a in attempts if a.round_number == session.current_round
    )
    round_scores = {
        "round_1": sum(1 for a in attempts if a.round_number == 1 and a.is_correct),
        "round_2": sum(1 for a in attempts if a.round_number == 2 and a.is_correct),
        "round_3": sum(1 for a in attempts if a.round_number == 3 and a.is_correct),
    }

    if total_attempts >= TOTAL_ITEMS:
        # Check if audit log already generated; if not, evaluate
        audit_log = (
            db.query(VerificationAuditLog)
            .filter(VerificationAuditLog.session_id == session.id)
            .first()
        )
        if not audit_log:
            result = evaluate_verification(db, session.id)
        else:
            result = VerificationResult.model_validate(audit_log)

        return VerificationStatusResponse(
            session_id=session.id,
            current_round=session.current_round,
            status=session.status,
            round_attempts=round_attempts_count,
            total_attempts=total_attempts,
            is_completed=True,
            is_verified=result.is_verified,
            cumulative_accuracy=result.cumulative_accuracy,
            round_scores=round_scores,
            verification_hash=result.verification_hash,
            audit_log=result,
        )

    correct_so_far = sum(1 for a in attempts if a.is_correct)
    accuracy = (
        round(correct_so_far / total_attempts * 100.0, 2)
        if total_attempts > 0
        else None
    )

    return VerificationStatusResponse(
        session_id=session.id,
        current_round=session.current_round,
        status=session.status,
        round_attempts=round_attempts_count,
        total_attempts=total_attempts,
        is_completed=False,
        is_verified=None,
        cumulative_accuracy=accuracy,
        round_scores=round_scores,
        verification_hash=None,
        audit_log=None,
    )
