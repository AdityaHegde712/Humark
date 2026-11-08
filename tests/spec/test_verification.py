"""Contract and unit/integration tests for verification state machine and round progression.

Tests verify:
1. Advancing round fails if current round has < 10 attempts (IncompleteRoundError / HTTP 400).
2. Advancing round succeeds when current round has exactly 10 attempts, moving 1 -> 2, then 2 -> 3.
3. Advancing beyond Round 3 raises MaxRoundsReachedError (HTTP 400).
4. Verification threshold >= 22/30 (e.g. 22 correct -> verified=true; 21 correct -> verified=false).
5. Tamper-evident verification audit log generation and hash integrity verification.
6. Verification status API endpoints (POST /api/sessions/advance-round and GET /api/sessions/verification).
"""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.game import get_or_create_session
from app.core.ingestion import ingest_batch
from app.core.verification import (
    IncompleteRoundError,
    MaxRoundsReachedError,
    VerificationIncompleteError,
    advance_round,
    compute_verification_hash,
    evaluate_verification,
    get_verification_status,
)
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.challenge import Challenge
from app.models.session import SessionAttempt
from app.models.verification import VerificationAuditLog


@pytest.fixture
def test_engine():
    """Create an isolated in-memory SQLite database engine with StaticPool."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_engine):
    """Create an isolated database session for testing."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seeded_db_30(db_session):
    """Seed database with 30 valid challenges for a complete 3-round benchmark."""
    challenges = []
    for i in range(1, 35):
        win_var = "A" if i % 2 == 1 else "B"
        clicks_a = 4000 if win_var == "A" else 3000
        clicks_b = 3000 if win_var == "A" else 4000
        challenges.append(
            {
                "id": f"c{i:04d}0000-0000-0000-0000-000000000000",
                "title": f"Verification Challenge {i:02d}",
                "category": "youtube_thumbnails",
                "thumbnail_a_url": f"/static/thumbnails/challenge_{i:02d}_a.svg",
                "thumbnail_b_url": f"/static/thumbnails/challenge_{i:02d}_b.svg",
                "impressions_a": 50000,
                "clicks_a": clicks_a,
                "impressions_b": 50000,
                "clicks_b": clicks_b,
                "provenance_source": f"Channel {i}",
            }
        )
    ingest_batch(challenges, db_session, precompute_baselines=False)
    return db_session


def populate_attempts(
    db, session_id: str, round_number: int, total_items: int = 10, correct_count: int = 8
):
    """Helper to populate attempts for a given round with controlled correctness."""
    challenges = (
        db.query(Challenge)
        .order_by(Challenge.id.asc())
        .offset((round_number - 1) * 10)
        .limit(total_items)
        .all()
    )

    for idx, ch in enumerate(challenges):
        # Determine whether to answer correctly or incorrectly
        if idx < correct_count:
            selected = ch.winning_variant
        else:
            selected = "B" if ch.winning_variant == "A" else "A"

        attempt = SessionAttempt(
            id=str(uuid.uuid4()),
            session_id=session_id,
            challenge_id=ch.id,
            round_number=round_number,
            selected_variant=selected,
            is_correct=(selected == ch.winning_variant),
            time_taken_ms=1200 + idx * 50,
        )
        db.add(attempt)
    db.commit()


# ---------------------------------------------------------------------------
# Unit Tests for State Machine & Verification Logic
# ---------------------------------------------------------------------------


def test_advance_round_fails_if_round_incomplete(seeded_db_30):
    """advance_round must fail if current round has fewer than 10 attempts."""
    session = get_or_create_session(seeded_db_30)
    # Populate only 5 attempts
    populate_attempts(
        seeded_db_30, session.id, round_number=1, total_items=5, correct_count=4
    )

    with pytest.raises(IncompleteRoundError) as exc_info:
        advance_round(seeded_db_30, session.id)

    assert "not complete" in str(exc_info.value).lower()
    assert session.current_round == 1


def test_advance_round_success_progression(seeded_db_30):
    """advance_round moves 1 -> 2 and 2 -> 3 when 10 attempts are completed."""
    session = get_or_create_session(seeded_db_30)

    # Complete Round 1 (10 attempts)
    populate_attempts(
        seeded_db_30, session.id, round_number=1, total_items=10, correct_count=8
    )

    # Advance to Round 2
    session = advance_round(seeded_db_30, session.id)
    assert session.current_round == 2
    assert session.status == "active"

    # Complete Round 2 (10 attempts)
    populate_attempts(
        seeded_db_30, session.id, round_number=2, total_items=10, correct_count=7
    )

    # Advance to Round 3
    session = advance_round(seeded_db_30, session.id)
    assert session.current_round == 3
    assert session.status == "active"


def test_cannot_advance_beyond_round_3(seeded_db_30):
    """Advancing beyond Round 3 must raise MaxRoundsReachedError."""
    session = get_or_create_session(seeded_db_30)

    # Complete rounds 1, 2, 3
    for r in range(1, 4):
        session.current_round = r
        seeded_db_30.commit()
        populate_attempts(
            seeded_db_30, session.id, round_number=r, total_items=10, correct_count=8
        )

    assert session.current_round == 3
    with pytest.raises(MaxRoundsReachedError) as exc_info:
        advance_round(seeded_db_30, session.id)

    assert "cannot advance beyond round 3" in str(exc_info.value).lower()


def test_evaluate_verification_incomplete_raises_error(seeded_db_30):
    """Evaluating verification with < 30 attempts must raise VerificationIncompleteError."""
    session = get_or_create_session(seeded_db_30)
    populate_attempts(
        seeded_db_30, session.id, round_number=1, total_items=10, correct_count=8
    )

    with pytest.raises(VerificationIncompleteError):
        evaluate_verification(seeded_db_30, session.id)


def test_verification_threshold_pass(seeded_db_30):
    """Session with >= 22/30 correct attempts is marked verified=True (status='verified')."""
    session = get_or_create_session(seeded_db_30)

    # Round 1: 8 correct, Round 2: 7 correct, Round 3: 7 correct -> Total 22 correct
    populate_attempts(
        seeded_db_30, session.id, round_number=1, total_items=10, correct_count=8
    )
    populate_attempts(
        seeded_db_30, session.id, round_number=2, total_items=10, correct_count=7
    )
    populate_attempts(
        seeded_db_30, session.id, round_number=3, total_items=10, correct_count=7
    )

    result = evaluate_verification(seeded_db_30, session.id)

    assert result.is_verified is True
    assert result.total_attempts == 30
    assert result.correct_attempts == 22
    assert result.cumulative_accuracy == pytest.approx(0.7333, rel=1e-2)
    assert result.round_1_correct == 8
    assert result.round_2_correct == 7
    assert result.round_3_correct == 7
    assert len(result.verification_hash) == 64

    # Check database state
    seeded_db_30.refresh(session)
    assert session.status == "verified"

    audit = (
        seeded_db_30.query(VerificationAuditLog)
        .filter_by(session_id=session.id)
        .first()
    )
    assert audit is not None
    assert audit.is_verified is True
    assert audit.verification_hash == result.verification_hash


def test_verification_threshold_fail(seeded_db_30):
    """Session with 21/30 correct attempts is marked verified=False (status='failed')."""
    session = get_or_create_session(seeded_db_30)

    # Round 1: 7 correct, Round 2: 7 correct, Round 3: 7 correct -> Total 21 correct
    populate_attempts(
        seeded_db_30, session.id, round_number=1, total_items=10, correct_count=7
    )
    populate_attempts(
        seeded_db_30, session.id, round_number=2, total_items=10, correct_count=7
    )
    populate_attempts(
        seeded_db_30, session.id, round_number=3, total_items=10, correct_count=7
    )

    result = evaluate_verification(seeded_db_30, session.id)

    assert result.is_verified is False
    assert result.total_attempts == 30
    assert result.correct_attempts == 21
    assert result.cumulative_accuracy == pytest.approx(0.7000, rel=1e-2)

    seeded_db_30.refresh(session)
    assert session.status == "failed"


def test_tamper_evident_verification_hash(seeded_db_30):
    """Tampering with an attempt changes the computed verification hash."""
    session = get_or_create_session(seeded_db_30)
    for r in range(1, 4):
        populate_attempts(
            seeded_db_30, session.id, round_number=r, total_items=10, correct_count=8
        )

    result = evaluate_verification(seeded_db_30, session.id)
    original_hash = result.verification_hash

    # Fetch attempts and compute hash
    attempts = (
        seeded_db_30.query(SessionAttempt)
        .filter_by(session_id=session.id)
        .order_by(SessionAttempt.round_number.asc(), SessionAttempt.challenge_id.asc())
        .all()
    )
    computed = compute_verification_hash(session.id, attempts)
    assert computed == original_hash

    # Tamper with an attempt (flip selected variant)
    attempts[0].selected_variant = "B" if attempts[0].selected_variant == "A" else "A"
    tampered_hash = compute_verification_hash(session.id, attempts)
    assert tampered_hash != original_hash


def test_get_verification_status_progression(seeded_db_30):
    """Test get_verification_status reports accurate round progression and breakdown."""
    session = get_or_create_session(seeded_db_30)
    status_0 = get_verification_status(seeded_db_30, session.id)
    assert status_0.is_completed is False
    assert status_0.total_attempts == 0
    assert status_0.round_attempts == 0
    assert status_0.round_scores == {"round_1": 0, "round_2": 0, "round_3": 0}

    # Populate 10 attempts in round 1
    populate_attempts(
        seeded_db_30, session.id, round_number=1, total_items=10, correct_count=8
    )
    status_1 = get_verification_status(seeded_db_30, session.id)
    assert status_1.is_completed is False
    assert status_1.total_attempts == 10
    assert status_1.round_scores["round_1"] == 8
    assert status_1.cumulative_accuracy == pytest.approx(0.8, rel=1e-2)


# ---------------------------------------------------------------------------
# API Integration Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_advance_round_flow(seeded_db_30):
    """API endpoint POST /api/sessions/advance-round advances round after completion."""

    def override_get_db():
        yield seeded_db_30

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        res = await client.post("/api/sessions")
        assert res.status_code == 201
        session_id = res.json()["id"]

        # Attempt to advance round before 10 attempts -> 400 Bad Request
        res_adv = await client.post(
            "/api/sessions/advance-round",
            headers={"X-Session-ID": session_id},
        )
        assert res_adv.status_code == 400
        assert "not complete" in res_adv.json()["detail"].lower()

        # Complete 10 attempts
        populate_attempts(
            seeded_db_30, session_id, round_number=1, total_items=10, correct_count=8
        )

        # Advance round -> 200 OK
        res_adv_ok = await client.post(
            "/api/sessions/advance-round",
            headers={"X-Session-ID": session_id},
        )
        assert res_adv_ok.status_code == 200
        data = res_adv_ok.json()
        assert data["current_round"] == 2
        assert data["status"] == "active"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_verification_endpoint(seeded_db_30):
    """API endpoint GET /api/sessions/verification returns progress and final audit."""

    def override_get_db():
        yield seeded_db_30

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        res = await client.post("/api/sessions")
        session_id = res.json()["id"]

        # Check verification progress with 0 items
        res_ver = await client.get(
            "/api/sessions/verification",
            headers={"X-Session-ID": session_id},
        )
        assert res_ver.status_code == 200
        data = res_ver.json()
        assert data["is_completed"] is False
        assert data["total_attempts"] == 0

        # Complete all 3 rounds (24/30 correct -> verified)
        for r in range(1, 4):
            populate_attempts(
                seeded_db_30, session_id, round_number=r, total_items=10, correct_count=8
            )

        # GET /api/sessions/verification now automatically finalizes / returns audit
        res_ver_final = await client.get(
            "/api/sessions/verification",
            headers={"X-Session-ID": session_id},
        )
        assert res_ver_final.status_code == 200
        final_data = res_ver_final.json()
        assert final_data["is_completed"] is True
        assert final_data["is_verified"] is True
        assert final_data["total_attempts"] == 30
        assert final_data["round_scores"]["round_1"] == 8
        assert final_data["round_scores"]["round_2"] == 8
        assert final_data["round_scores"]["round_3"] == 8
        assert final_data["verification_hash"] is not None
        assert final_data["audit_log"] is not None

    app.dependency_overrides.clear()
