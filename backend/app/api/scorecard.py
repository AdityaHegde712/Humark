"""API endpoints for session scorecard telemetry and public shareable results."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.sessions import get_request_session_id
from app.core.scoring import SessionNotFoundError, calculate_session_scorecard
from app.db.session import get_db
from app.schemas.scorecard import ScorecardResponse

router = APIRouter(prefix="/api/scorecard", tags=["scorecard"])


@router.get(
    "",
    response_model=ScorecardResponse,
    summary="Get performance scorecard for active session",
)
def get_current_session_scorecard(
    db: Session = Depends(get_db),
    session_id: str | None = Depends(get_request_session_id),
) -> ScorecardResponse:
    """Retrieve performance scorecard, Wilson confidence interval, and model comparisons."""
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session ID required via X-Session-ID header or cookie",
        )

    try:
        return calculate_session_scorecard(db, session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/{session_id}",
    response_model=ScorecardResponse,
    summary="Get shareable public scorecard by session ID",
)
def get_public_session_scorecard(
    session_id: str,
    db: Session = Depends(get_db),
) -> ScorecardResponse:
    """Retrieve public shareable scorecard without requiring visitor authentication."""
    try:
        return calculate_session_scorecard(db, session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
