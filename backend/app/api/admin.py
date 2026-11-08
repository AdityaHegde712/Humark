"""Admin API endpoints for dataset ingestion and maintenance."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.ingestion import ingest_batch
from app.db.session import get_db
from app.schemas.challenge import ChallengeCreate, IngestionRequest, IngestionSummary

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post(
    "/ingest",
    response_model=IngestionSummary,
    status_code=status.HTTP_200_OK,
    summary="Ingest batch of candidate challenges",
    description="Validate significance gate (ADR-002) and ingest challenges into database.",
)
async def ingest_challenges(
    payload: IngestionRequest | list[ChallengeCreate] | dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
) -> IngestionSummary:
    """Ingest candidate challenges with automated significance gate validation."""
    if isinstance(payload, IngestionRequest):
        items = payload.challenges
    elif isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and "challenges" in payload:
        items = payload["challenges"]
    else:
        items = [payload]

    return ingest_batch(items, db)
