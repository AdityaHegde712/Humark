"""API endpoints for challenge presentation and attempt submission."""

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.sessions import get_request_session_id
from app.core.game import (
    ChallengeNotFoundError,
    DuplicateAttemptError,
    RoundCompletedError,
    SessionNotFoundError,
    get_next_unseen_challenge,
    get_or_create_session,
    record_attempt,
)
from app.db.session import get_db
from app.models.session import SessionAttempt
from app.schemas.session import (
    AttemptCreate,
    AttemptReceipt,
    NextChallengeResponse,
)

router = APIRouter(prefix="/api/challenges", tags=["challenges"])


@router.get(
    "/next",
    response_model=NextChallengeResponse,
    summary="Get next unseen challenge for active session",
    description="Returns public challenge data concealing all ground truth metrics.",
)
def get_next_challenge(
    response: Response,
    db: Session = Depends(get_db),
    session_id: str | None = Depends(get_request_session_id),
) -> NextChallengeResponse:
    """Retrieve the next unseen challenge or indicate round completion."""
    session = get_or_create_session(db, session_id)

    # Attach session to response headers and cookie if new
    response.set_cookie(
        key="humark_session_id",
        value=session.id,
        httponly=False,
        samesite="lax",
    )
    response.headers["X-Session-ID"] = session.id

    challenge = get_next_unseen_challenge(db, session.id)

    if not challenge:
        return NextChallengeResponse(
            round_completed=True,
            round_number=session.current_round,
            attempt_index=10,
            total_round_items=10,
        )

    # Calculate current attempt index within the active round (1-indexed)
    round_attempts = (
        db.query(SessionAttempt)
        .filter(
            SessionAttempt.session_id == session.id,
            SessionAttempt.round_number == session.current_round,
        )
        .count()
    )

    return NextChallengeResponse(
        id=challenge.id,
        title=challenge.title,
        category=challenge.category,
        thumbnail_a_url=challenge.thumbnail_a_url,
        thumbnail_b_url=challenge.thumbnail_b_url,
        round_completed=False,
        round_number=session.current_round,
        attempt_index=round_attempts + 1,
        total_round_items=10,
    )


@router.post(
    "/{challenge_id}/attempt",
    response_model=AttemptReceipt,
    summary="Submit user attempt and reveal immediate receipt",
    description="Grades decision against ground truth and returns model comparison metrics.",
)
def submit_attempt(
    challenge_id: str,
    payload: AttemptCreate,
    response: Response,
    db: Session = Depends(get_db),
    session_id: str | None = Depends(get_request_session_id),
) -> AttemptReceipt:
    """Submit variant choice ('A' or 'B') and retrieve full verification receipt."""
    session = get_or_create_session(db, session_id)

    # Ensure session identifier is set on response
    response.set_cookie(
        key="humark_session_id",
        value=session.id,
        httponly=False,
        samesite="lax",
    )
    response.headers["X-Session-ID"] = session.id

    try:
        receipt = record_attempt(
            db=db,
            session_id=session.id,
            challenge_id=challenge_id,
            selected_variant=payload.selected_variant,
            time_taken_ms=payload.time_taken_ms,
        )
        return receipt
    except DuplicateAttemptError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except RoundCompletedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (ChallengeNotFoundError, SessionNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
