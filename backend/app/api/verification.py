"""API endpoints for round progression and verification audit inspection."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.sessions import get_request_session_id
from app.core.verification import (
    IncompleteRoundError,
    MaxRoundsReachedError,
    SessionNotFoundError,
    VerificationIncompleteError,
    advance_round,
    evaluate_verification,
    get_verification_status,
)
from app.db.session import get_db
from app.schemas.verification import (
    RoundAdvanceResponse,
    VerificationResult,
    VerificationStatusResponse,
)

router = APIRouter(prefix="/api/sessions", tags=["verification"])


class AdvanceRoundRequest(BaseModel):
    """Optional request body containing explicit session ID."""

    session_id: str | None = Field(default=None, description="Explicit session ID")


@router.post(
    "/advance-round",
    response_model=RoundAdvanceResponse,
    summary="Advance session to the next benchmark round",
)
def advance_session_round(
    request: Request,
    body: AdvanceRoundRequest | None = None,
    db: Session = Depends(get_db),
    session_id: str | None = Depends(get_request_session_id),
) -> RoundAdvanceResponse:
    """Advance active session to the next round once current round is complete."""
    target_id = (body.session_id if body and body.session_id else None) or session_id
    if not target_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session ID required via X-Session-ID header, cookie, or request body",
        )

    try:
        session = advance_round(db, target_id)
        return RoundAdvanceResponse(
            session_id=session.id,
            current_round=session.current_round,
            status=session.status,
            message=f"Advanced to round {session.current_round}",
        )
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (IncompleteRoundError, MaxRoundsReachedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/verification",
    response_model=VerificationStatusResponse,
    summary="Get verification track progress, round scores, and audit log",
)
def get_session_verification_status(
    request: Request,
    session_id_query: str | None = Query(None, alias="session_id"),
    db: Session = Depends(get_db),
    session_id: str | None = Depends(get_request_session_id),
) -> VerificationStatusResponse:
    """Retrieve round progression and tamper-evident verification receipt."""
    target_id = session_id_query or session_id
    if not target_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session ID required via X-Session-ID header, cookie, or session_id query param",
        )

    try:
        return get_verification_status(db, target_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/verification/evaluate",
    response_model=VerificationResult,
    summary="Explicitly evaluate verification track and produce audit log",
)
def evaluate_session_verification(
    request: Request,
    body: AdvanceRoundRequest | None = None,
    db: Session = Depends(get_db),
    session_id: str | None = Depends(get_request_session_id),
) -> VerificationResult:
    """Explicitly trigger verification evaluation and audit log generation."""
    target_id = (body.session_id if body and body.session_id else None) or session_id
    if not target_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session ID required via X-Session-ID header, cookie, or request body",
        )

    try:
        return evaluate_verification(db, target_id)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except VerificationIncompleteError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
