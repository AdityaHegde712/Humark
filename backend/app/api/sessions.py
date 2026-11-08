"""API endpoints for session creation and progress telemetry."""

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.game import (
    SessionNotFoundError,
    get_or_create_session,
    get_session_stats,
)
from app.db.session import get_db
from app.schemas.session import GameSessionResponse

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def get_request_session_id(
    request: Request,
    x_session_id: str | None = Header(None, alias="X-Session-ID"),
) -> str | None:
    """Resolve session ID from header or cookie."""
    if x_session_id and x_session_id.strip():
        return x_session_id.strip()
    cookie_id = request.cookies.get("humark_session_id")
    if cookie_id and cookie_id.strip():
        return cookie_id.strip()
    return None


@router.post(
    "",
    response_model=GameSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize or retrieve guest session",
)
def create_session(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    session_id: str | None = Depends(get_request_session_id),
) -> GameSessionResponse:
    """Create a new game session or return the existing one for the visitor."""
    session = get_or_create_session(db, session_id)

    # Set cookie and header for stateless client tracking
    response.set_cookie(
        key="humark_session_id",
        value=session.id,
        httponly=False,
        samesite="lax",
    )
    response.headers["X-Session-ID"] = session.id

    stats = get_session_stats(db, session.id)
    return GameSessionResponse(**stats)


@router.get(
    "/current",
    response_model=GameSessionResponse,
    summary="Retrieve current session state and progress",
)
def get_current_session(
    db: Session = Depends(get_db),
    session_id: str | None = Depends(get_request_session_id),
) -> GameSessionResponse:
    """Return progress and status of active session."""
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session ID required via X-Session-ID header or humark_session_id cookie",
        )
    try:
        stats = get_session_stats(db, session_id)
        return GameSessionResponse(**stats)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
