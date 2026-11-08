"""Visual motif tagging and failure-mode analysis engine for Humark benchmark."""

from __future__ import annotations

from typing import Literal
from sqlalchemy.orm import Session

from app.eval.prompts import PROMPT_VERSION
from app.models.challenge import Challenge, ModelPrediction
from app.models.session import SessionAttempt
from app.schemas.scorecard import MotifPerformanceItem

DEFAULT_FRONTIER_MODEL = "mock-frontier-v1"

CANONICAL_MOTIFS: dict[str, dict[str, str]] = {
    "face_emotion": {
        "name": "Face & Emotion",
        "insight": "Human intuition excels at decoding authentic micro-expressions and social tension that vision models miss.",
    },
    "curiosity_gap": {
        "name": "Curiosity Gap",
        "insight": "Humans resonate strongly with unanswered narrative questions and intrigue that vision models often penalize as ambiguous.",
    },
    "text_contrast": {
        "name": "Text Contrast",
        "insight": "Frontier vision models excel at OCR and typography contrast, but human perception weighs cognitive load and glance readability.",
    },
    "visual_complexity": {
        "name": "Visual Complexity",
        "insight": "Dense compositions create visual noise for human viewers at 100ms glance speeds, while vision models reward element density.",
    },
}

# Canonical presentation order
MOTIF_ORDER: list[str] = [
    "face_emotion",
    "curiosity_gap",
    "text_contrast",
    "visual_complexity",
]


def determine_motif_verdict(
    accuracy_delta: float,
) -> Literal["human_dominant", "ai_dominant", "parity"]:
    """Classify advantage verdict using +/- 0.05 margin threshold."""
    if accuracy_delta > 0.05:
        return "human_dominant"
    elif accuracy_delta < -0.05:
        return "ai_dominant"
    return "parity"


def calculate_motif_breakdown(
    db: Session,
    session_id: str,
    frontier_model: str = DEFAULT_FRONTIER_MODEL,
) -> list[MotifPerformanceItem]:
    """Compute performance breakdown and human-vs-frontier advantage by visual motif.

    Args:
        db: Active SQLAlchemy database session.
        session_id: Game session identifier string.
        frontier_model: Model identifier for comparative baseline (default mock-frontier-v1).

    Returns:
        List of MotifPerformanceItem records for all motifs encountered in the session.
    """
    attempts = (
        db.query(SessionAttempt)
        .filter(SessionAttempt.session_id == session_id)
        .order_by(SessionAttempt.created_at.asc())
        .all()
    )

    if not attempts:
        return []

    challenge_ids = list({a.challenge_id for a in attempts})
    challenges = (
        db.query(Challenge).filter(Challenge.id.in_(challenge_ids)).all()
        if challenge_ids
        else []
    )
    challenge_map: dict[str, Challenge] = {c.id: c for c in challenges}

    # Fetch baseline frontier predictions for these challenges
    predictions = (
        db.query(ModelPrediction)
        .filter(
            ModelPrediction.challenge_id.in_(challenge_ids),
            ModelPrediction.model_name == frontier_model,
        )
        .all()
        if challenge_ids
        else []
    )

    frontier_map: dict[str, ModelPrediction] = {}
    for p in predictions:
        existing = frontier_map.get(p.challenge_id)
        if existing is None or p.prompt_version == PROMPT_VERSION:
            frontier_map[p.challenge_id] = p

    # Accumulate metrics per motif
    # Structure: {motif_key: {"total": 0, "user_correct": 0, "frontier_correct": 0}}
    motif_stats: dict[str, dict[str, int]] = {}

    for attempt in attempts:
        ch = challenge_map.get(attempt.challenge_id)
        if not ch:
            continue

        motif = ch.primary_motif or "visual_contrast"
        if motif not in motif_stats:
            motif_stats[motif] = {
                "total": 0,
                "user_correct": 0,
                "frontier_correct": 0,
            }

        motif_stats[motif]["total"] += 1
        if attempt.is_correct:
            motif_stats[motif]["user_correct"] += 1

        pred = frontier_map.get(ch.id)
        if pred and pred.predicted_variant.upper() == ch.winning_variant.upper():
            motif_stats[motif]["frontier_correct"] += 1

    # Sort motifs following canonical order, appending any unforeseen motifs at the end
    sorted_motifs = [m for m in MOTIF_ORDER if m in motif_stats]
    for m in motif_stats:
        if m not in sorted_motifs:
            sorted_motifs.append(m)

    breakdown: list[MotifPerformanceItem] = []
    for motif in sorted_motifs:
        stats = motif_stats[motif]
        tot = stats["total"]
        if tot == 0:
            continue

        user_cor = stats["user_correct"]
        front_cor = stats["frontier_correct"]

        user_acc = round(user_cor / tot, 4)
        front_acc = round(front_cor / tot, 4)
        delta = round(user_acc - front_acc, 4)
        verdict = determine_motif_verdict(delta)

        config = CANONICAL_MOTIFS.get(motif, {})
        motif_name = config.get("name", motif.replace("_", " ").title())
        insight = config.get(
            "insight",
            "Human visual intuition compared with automated baseline models.",
        )

        breakdown.append(
            MotifPerformanceItem(
                motif=motif,
                motif_name=motif_name,
                total_attempts=tot,
                user_correct=user_cor,
                user_accuracy=user_acc,
                frontier_accuracy=front_acc,
                accuracy_delta=delta,
                verdict=verdict,
                insight=insight,
            )
        )

    return breakdown
