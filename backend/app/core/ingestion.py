"""Challenge ingestion engine enforcing statistical significance and provenance gates."""

from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.stats import validate_significance_gate
from app.models.challenge import Challenge
from app.schemas.challenge import ChallengeCreate, IngestionSummary


class IngestionError(Exception):
    """Exception raised when a challenge candidate violates ingestion criteria."""


def ingest_challenge_item(
    item_data: ChallengeCreate | dict[str, Any],
    db: Session,
) -> Challenge:
    """Validate and ingest a single challenge candidate into the database.

    Enforces ADR-002: Hard significance gate (N >= 20,000, p < 0.05).
    Computes CTRs, winning variant, z-score, and p-value automatically.

    Args:
        item_data: ChallengeCreate schema instance or raw dictionary.
        db: Active SQLAlchemy database session.

    Returns:
        Persisted Challenge model instance.

    Raises:
        IngestionError: If the challenge violates schema, provenance, or significance criteria.
    """
    if isinstance(item_data, dict):
        # Explicitly check provenance source presence
        prov = item_data.get("provenance_source")
        if not prov or not str(prov).strip():
            raise IngestionError(
                "Missing or invalid provenance metadata (provenance_source required)"
            )

        try:
            item = ChallengeCreate(**item_data)
        except ValidationError as e:
            error_msgs = "; ".join(
                [f"{err['loc'][-1]}: {err['msg']}" for err in e.errors()]
            )
            raise IngestionError(f"Validation error: {error_msgs}") from e
    else:
        item = item_data
        if not item.provenance_source or not item.provenance_source.strip():
            raise IngestionError(
                "Missing or invalid provenance metadata (provenance_source required)"
            )

    # Enforce statistical significance hard gate (ADR-002)
    gate = validate_significance_gate(
        impressions_a=item.impressions_a,
        clicks_a=item.clicks_a,
        impressions_b=item.impressions_b,
        clicks_b=item.clicks_b,
    )

    if not gate.is_valid:
        raise IngestionError(gate.rejection_reason or "Failed significance gate")

    ctr_a = gate.z_test_result.ctr_a
    ctr_b = gate.z_test_result.ctr_b
    winning_variant = "A" if ctr_a > ctr_b else "B"

    # Check if item with this ID already exists (idempotent upsert)
    challenge: Challenge | None = None
    if item.id:
        challenge = db.query(Challenge).filter_by(id=item.id).first()

    if challenge is None:
        challenge = Challenge(
            id=item.id,
            title=item.title,
            category=item.category,
            thumbnail_a_url=item.thumbnail_a_url,
            thumbnail_b_url=item.thumbnail_b_url,
            impressions_a=item.impressions_a,
            clicks_a=item.clicks_a,
            ctr_a=ctr_a,
            impressions_b=item.impressions_b,
            clicks_b=item.clicks_b,
            ctr_b=ctr_b,
            winning_variant=winning_variant,
            z_score=gate.z_test_result.z_score,
            p_value=gate.z_test_result.p_value,
            provenance_source=item.provenance_source,
            is_active=True,
        )
        db.add(challenge)
    else:
        challenge.title = item.title
        challenge.category = item.category
        challenge.thumbnail_a_url = item.thumbnail_a_url
        challenge.thumbnail_b_url = item.thumbnail_b_url
        challenge.impressions_a = item.impressions_a
        challenge.clicks_a = item.clicks_a
        challenge.ctr_a = ctr_a
        challenge.impressions_b = item.impressions_b
        challenge.clicks_b = item.clicks_b
        challenge.ctr_b = ctr_b
        challenge.winning_variant = winning_variant
        challenge.z_score = gate.z_test_result.z_score
        challenge.p_value = gate.z_test_result.p_value
        challenge.provenance_source = item.provenance_source
        challenge.is_active = True

    db.commit()
    db.refresh(challenge)
    return challenge


def ingest_batch(
    items: list[ChallengeCreate | dict[str, Any]],
    db: Session,
) -> IngestionSummary:
    """Ingest a batch of challenge items, tracking successes and rejections.

    Args:
        items: List of challenge items (dictionaries or schemas).
        db: Active SQLAlchemy database session.

    Returns:
        IngestionSummary containing counts and rejection details.
    """
    ingested_ids: list[str] = []
    rejections: list[dict[str, Any]] = []

    for idx, item in enumerate(items):
        title = (
            item.title
            if isinstance(item, ChallengeCreate)
            else item.get("title", f"Item #{idx}")
        )
        try:
            challenge = ingest_challenge_item(item, db)
            ingested_ids.append(challenge.id)
        except (IngestionError, ValueError, ValidationError, KeyError) as err:
            rejections.append(
                {
                    "index": idx,
                    "title": title,
                    "reason": str(err),
                }
            )

    return IngestionSummary(
        total_submitted=len(items),
        ingested_count=len(ingested_ids),
        rejected_count=len(rejections),
        ingested_ids=ingested_ids,
        rejections=rejections,
    )
