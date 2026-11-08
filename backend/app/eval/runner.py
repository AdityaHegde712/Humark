"""Evaluation runner service for Humark challenge baselines.

Implements baseline execution, caching, persistence, and batch evaluation
tracking for all challenge items.
"""

from typing import Any
import uuid

from sqlalchemy.orm import Session

from app.eval.mock_models import MOCK_MODELS, evaluate_mock_model
from app.eval.prompts import PROMPT_VERSION
from app.models.challenge import Challenge, ModelPrediction
from app.models.eval_run import EvalRun

DEFAULT_BASELINE_MODELS: list[str] = [
    "mock-frontier-v1",
    "mock-compact-v1",
    "mock-heuristic-v1",
]


def run_baseline_models_for_challenge(
    challenge: Challenge,
    db: Session,
    models: list[str] | None = None,
) -> list[ModelPrediction]:
    """Run baseline vision models on a single challenge and persist predictions.

    Idempotent: If a prediction for (challenge_id, model_name, prompt_version)
    already exists in the database, it is retrieved and reused.

    Args:
        challenge: Challenge database model instance.
        db: Active SQLAlchemy database session.
        models: Optional list of model names to run. Defaults to all 3 baselines.

    Returns:
        List of persisted ModelPrediction instances.
    """
    target_models = models or DEFAULT_BASELINE_MODELS
    results: list[ModelPrediction] = []

    for model_name in target_models:
        # Check if prediction already exists (idempotency check)
        existing = (
            db.query(ModelPrediction)
            .filter_by(
                challenge_id=challenge.id,
                model_name=model_name,
                prompt_version=PROMPT_VERSION,
            )
            .first()
        )

        if existing is not None:
            results.append(existing)
            continue

        if model_name in MOCK_MODELS:
            eval_res = evaluate_mock_model(challenge, model_name)
            pred = ModelPrediction(
                id=str(uuid.uuid4()),
                challenge_id=challenge.id,
                model_name=eval_res.model_name,
                model_version=eval_res.model_version,
                predicted_variant=eval_res.predicted_variant,
                confidence=eval_res.confidence,
                reasoning=eval_res.reasoning,
                prompt_version=eval_res.prompt_version,
                token_count=eval_res.token_count,
                latency_ms=eval_res.latency_ms,
                cost_usd=eval_res.cost_usd,
            )
            db.add(pred)
            results.append(pred)
        else:
            raise ValueError(f"Unsupported model '{model_name}' for baseline runner.")

    db.commit()
    for pred in results:
        db.refresh(pred)

    return results


def run_baselines_for_all_challenges(
    db: Session,
    models: list[str] | None = None,
) -> dict[str, Any]:
    """Batch run baseline models across all active challenges in the database.

    Creates an EvalRun record per evaluated model to track benchmark aggregates.

    Args:
        db: Active SQLAlchemy database session.
        models: Optional list of model names to run. Defaults to all 3 baselines.

    Returns:
        Summary dictionary of batch run counts.
    """
    target_models = models or DEFAULT_BASELINE_MODELS
    challenges = db.query(Challenge).filter_by(is_active=True).all()

    total_created = 0
    total_reused = 0

    # Model tracking aggregates for EvalRun
    model_stats: dict[str, dict[str, Any]] = {
        m: {
            "total": 0,
            "correct": 0,
            "tokens": 0,
            "cost": 0.0,
            "total_latency": 0,
        }
        for m in target_models
    }

    for c in challenges:
        for m in target_models:
            existing = (
                db.query(ModelPrediction)
                .filter_by(
                    challenge_id=c.id,
                    model_name=m,
                    prompt_version=PROMPT_VERSION,
                )
                .first()
            )

            if existing is not None:
                total_reused += 1
                pred = existing
            else:
                eval_res = evaluate_mock_model(c, m)
                pred = ModelPrediction(
                    id=str(uuid.uuid4()),
                    challenge_id=c.id,
                    model_name=eval_res.model_name,
                    model_version=eval_res.model_version,
                    predicted_variant=eval_res.predicted_variant,
                    confidence=eval_res.confidence,
                    reasoning=eval_res.reasoning,
                    prompt_version=eval_res.prompt_version,
                    token_count=eval_res.token_count,
                    latency_ms=eval_res.latency_ms,
                    cost_usd=eval_res.cost_usd,
                )
                db.add(pred)
                total_created += 1

            stats = model_stats[m]
            stats["total"] += 1
            if pred.predicted_variant == c.winning_variant:
                stats["correct"] += 1
            stats["tokens"] += pred.token_count
            stats["cost"] += pred.cost_usd
            stats["total_latency"] += pred.latency_ms

    db.commit()

    # Record EvalRun batch summaries
    for m, stats in model_stats.items():
        total_items = stats["total"]
        if total_items > 0:
            accuracy = round(stats["correct"] / total_items, 4)
            avg_latency = round(stats["total_latency"] / total_items, 2)
            eval_run = EvalRun(
                id=str(uuid.uuid4()),
                model_name=m,
                prompt_version=PROMPT_VERSION,
                total_challenges=total_items,
                correct_count=stats["correct"],
                accuracy=accuracy,
                total_tokens=stats["tokens"],
                total_cost_usd=round(stats["cost"], 6),
                avg_latency_ms=avg_latency,
            )
            db.add(eval_run)

    db.commit()

    return {
        "total_challenges": len(challenges),
        "predictions_created": total_created,
        "predictions_reused": total_reused,
        "models": target_models,
    }
