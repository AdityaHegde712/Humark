"""Core scorecard aggregator service for Humark benchmark telemetry and model comparisons."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.stats import calculate_wilson_score_interval
from app.core.verification import (
    ITEMS_PER_ROUND,
    MAX_ROUNDS,
    TOTAL_ITEMS,
    evaluate_verification,
)
from app.eval.prompts import PROMPT_VERSION
from app.models.challenge import Challenge, ModelPrediction
from app.models.session import GameSession, SessionAttempt
from app.schemas.scorecard import (
    CategoryBreakdownItem,
    ModelComparisonItem,
    ScorecardResponse,
    VerificationAuditSummary,
)


class ScorecardError(Exception):
    """Base exception for scorecard calculations."""

    pass


class SessionNotFoundError(ScorecardError):
    """Raised when the requested session is not found in the database."""

    pass


def calculate_session_scorecard(db: Session, session_id: str) -> ScorecardResponse:
    """Compute benchmark performance metrics, Wilson confidence intervals, and model comparisons.

    Args:
        db: Active SQLAlchemy database session.
        session_id: Unique session identifier string.

    Returns:
        ScorecardResponse containing overall accuracy, Wilson score interval,
        per-model head-to-head metrics, category breakdown, and verification audit.

    Raises:
        SessionNotFoundError: If the session does not exist in the database.
    """
    session = db.query(GameSession).filter(GameSession.id == session_id).first()
    if not session:
        raise SessionNotFoundError(f"Session '{session_id}' not found")

    attempts = (
        db.query(SessionAttempt)
        .filter(SessionAttempt.session_id == session.id)
        .order_by(SessionAttempt.created_at.asc())
        .all()
    )

    total_attempts = len(attempts)
    correct_attempts = sum(1 for a in attempts if a.is_correct)
    accuracy = (
        round(float(correct_attempts / total_attempts), 4)
        if total_attempts > 0
        else 0.0
    )
    average_time_taken_ms = (
        round(float(sum(a.time_taken_ms for a in attempts) / total_attempts), 2)
        if total_attempts > 0
        else 0.0
    )

    wilson_interval = calculate_wilson_score_interval(
        successes=correct_attempts,
        total=total_attempts,
        confidence=0.95,
    )

    rounds_completed = 0
    for r in range(1, MAX_ROUNDS + 1):
        round_items_count = sum(1 for a in attempts if a.round_number == r)
        if round_items_count >= ITEMS_PER_ROUND:
            rounds_completed += 1

    # Auto-evaluate verification audit if all 30 items completed but log was not yet generated
    if session.verification_audit is None and total_attempts >= TOTAL_ITEMS:
        try:
            evaluate_verification(db, session.id)
            db.refresh(session)
        except Exception:
            pass

    # Extract verification status and audit summary
    is_verified = False
    verification_hash: str | None = None
    verification_audit_summary: VerificationAuditSummary | None = None

    if session.verification_audit is not None:
        audit = session.verification_audit
        is_verified = audit.is_verified
        verification_hash = audit.verification_hash
        verification_audit_summary = VerificationAuditSummary(
            verification_hash=audit.verification_hash,
            completed_at=audit.completed_at,
            cumulative_accuracy=audit.cumulative_accuracy,
            round_1_correct=audit.round_1_correct,
            round_2_correct=audit.round_2_correct,
            round_3_correct=audit.round_3_correct,
        )
    elif session.status == "verified":
        is_verified = True

    # Pre-fetch challenges for category breakdown and winning variants
    challenge_ids = [a.challenge_id for a in attempts]
    challenges = (
        db.query(Challenge).filter(Challenge.id.in_(challenge_ids)).all()
        if challenge_ids
        else []
    )
    challenge_map: dict[str, Challenge] = {c.id: c for c in challenges}

    # Head-to-head model comparison
    model_comparisons: list[ModelComparisonItem] = []
    if challenge_ids:
        predictions = (
            db.query(ModelPrediction)
            .filter(ModelPrediction.challenge_id.in_(challenge_ids))
            .all()
        )

        # Group predictions by model_name and challenge_id
        model_predictions_map: dict[str, dict[str, ModelPrediction]] = {}
        for p in predictions:
            if p.model_name not in model_predictions_map:
                model_predictions_map[p.model_name] = {}
            # Prioritize matching prompt_version if multiple exist
            existing = model_predictions_map[p.model_name].get(p.challenge_id)
            if existing is None or p.prompt_version == PROMPT_VERSION:
                model_predictions_map[p.model_name][p.challenge_id] = p

        for model_name in sorted(model_predictions_map.keys()):
            preds_for_model = model_predictions_map[model_name]
            user_beat_model = 0
            model_beat_user = 0
            ties = 0
            model_correct_count = 0
            user_correct_count = 0
            evaluated_count = 0

            for a in attempts:
                if a.challenge_id not in preds_for_model:
                    continue

                evaluated_count += 1
                pred = preds_for_model[a.challenge_id]
                ch = challenge_map.get(a.challenge_id)
                winning_variant = ch.winning_variant.upper() if ch else "A"

                model_is_correct = pred.predicted_variant.upper() == winning_variant
                user_is_correct = a.is_correct

                if user_is_correct:
                    user_correct_count += 1
                if model_is_correct:
                    model_correct_count += 1

                if user_is_correct and not model_is_correct:
                    user_beat_model += 1
                elif model_is_correct and not user_is_correct:
                    model_beat_user += 1
                else:
                    ties += 1

            if evaluated_count > 0:
                model_accuracy = round(model_correct_count / evaluated_count, 4)
                user_subset_accuracy = round(user_correct_count / evaluated_count, 4)
                accuracy_delta = round(user_subset_accuracy - model_accuracy, 4)

                if accuracy_delta > 0:
                    verdict = "ahead"
                elif accuracy_delta < 0:
                    verdict = "behind"
                else:
                    verdict = "tied"

                model_comparisons.append(
                    ModelComparisonItem(
                        model_name=model_name,
                        model_accuracy=model_accuracy,
                        user_beat_model=user_beat_model,
                        model_beat_user=model_beat_user,
                        ties=ties,
                        accuracy_delta=accuracy_delta,
                        verdict=verdict,
                    )
                )

    # Category breakdown
    cat_aggregates: dict[str, dict[str, int]] = {}
    for a in attempts:
        ch = challenge_map.get(a.challenge_id)
        cat_name = ch.category if ch and ch.category else "youtube_thumbnails"
        if cat_name not in cat_aggregates:
            cat_aggregates[cat_name] = {"total": 0, "correct": 0}
        cat_aggregates[cat_name]["total"] += 1
        if a.is_correct:
            cat_aggregates[cat_name]["correct"] += 1

    category_breakdown: list[CategoryBreakdownItem] = []
    for cat_name in sorted(cat_aggregates.keys()):
        tot = cat_aggregates[cat_name]["total"]
        cor = cat_aggregates[cat_name]["correct"]
        cat_accuracy = round(cor / tot, 4) if tot > 0 else 0.0
        category_breakdown.append(
            CategoryBreakdownItem(
                category=cat_name,
                total_attempts=tot,
                correct_attempts=cor,
                accuracy=cat_accuracy,
            )
        )

    return ScorecardResponse(
        session_id=session.id,
        total_attempts=total_attempts,
        correct_attempts=correct_attempts,
        accuracy=accuracy,
        wilson_interval=wilson_interval,
        average_time_taken_ms=average_time_taken_ms,
        current_round=session.current_round,
        rounds_completed=rounds_completed,
        status=session.status,
        is_verified=is_verified,
        model_comparisons=model_comparisons,
        category_breakdown=category_breakdown,
        verification_audit=verification_audit_summary,
        verification_hash=verification_hash,
    )
