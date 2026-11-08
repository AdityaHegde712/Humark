"""Contract and integration tests for game engine and session management.

Tests verify:
1. Session creation and guest auto-generation via headers, cookies, or default.
2. Unseen-item selection: Attempted challenges are never returned to the same session.
3. Round boundary: Round threshold of 10 items stops returning unseen challenges and marks round completed.
4. Double-attempt rejection: Attempting the same challenge twice in one session raises HTTP 409 Conflict / DuplicateAttemptError.
5. Receipt reveal: Submitting an attempt immediately returns ground truth (CTRs, p-value, impressions)
   and attached model predictions with is_model_correct flags.
6. Public challenge endpoint: GET /api/challenges/next strictly hides ground truth.
"""

import pytest
from app.core.game import (
    DuplicateAttemptError,
    RoundCompletedError,
    create_new_session,
    get_next_unseen_challenge,
    get_or_create_session,
    record_attempt,
)
from app.core.ingestion import ingest_batch
from app.db.base import Base
from app.db.session import get_db
from app.eval.runner import run_baselines_for_all_challenges
from app.main import app
from app.models.challenge import Challenge
from app.models.session import GameSession, SessionAttempt
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


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
def seeded_db(db_session):
    """Seed database with 15 valid challenges and baseline model predictions."""
    challenges = []
    for i in range(1, 16):
        # Alternate winning variants
        win_var = "A" if i % 2 == 1 else "B"
        clicks_a = 4000 if win_var == "A" else 3000
        clicks_b = 3000 if win_var == "A" else 4000
        challenges.append(
            {
                "id": f"c{i:04d}0000-0000-0000-0000-000000000000",
                "title": f"Benchmark Challenge {i:02d}",
                "category": "youtube_thumbnails",
                "thumbnail_a_url": f"/static/thumbnails/challenge_{i:02d}_a.svg",
                "thumbnail_b_url": f"/static/thumbnails/challenge_{i:02d}_b.svg",
                "impressions_a": 50000,
                "clicks_a": clicks_a,
                "impressions_b": 50000,
                "clicks_b": clicks_b,
                "provenance_source": f"Seed Channel {i} (DEMO DATA)",
            }
        )
    ingest_batch(challenges, db_session, precompute_baselines=False)
    run_baselines_for_all_challenges(db_session)
    return db_session


# ---------------------------------------------------------------------------
# Core Engine Unit Tests
# ---------------------------------------------------------------------------


def test_session_creation_and_retrieval(db_session):
    """Test get_or_create_session creates a session when none provided and retrieves existing."""
    # 1. Create brand new guest session
    new_session = get_or_create_session(db_session, None)
    assert new_session is not None
    assert new_session.id is not None
    assert new_session.current_round == 1
    assert new_session.status == "active"

    # 2. Retrieve existing session
    retrieved = get_or_create_session(db_session, new_session.id)
    assert retrieved.id == new_session.id
    assert retrieved.current_round == 1


def test_unseen_item_selection_never_repeats_attempted(seeded_db):
    """Ensure get_next_unseen_challenge never returns any challenge already attempted by session."""
    session = get_or_create_session(seeded_db, None)

    attempted_ids = set()
    for _ in range(5):
        next_challenge = get_next_unseen_challenge(seeded_db, session.id)
        assert next_challenge is not None
        assert next_challenge.id not in attempted_ids

        # Attempt this challenge
        receipt = record_attempt(
            db=seeded_db,
            session_id=session.id,
            challenge_id=next_challenge.id,
            selected_variant="A",
            time_taken_ms=1250,
        )
        assert receipt.challenge_id == next_challenge.id
        attempted_ids.add(next_challenge.id)

    # Next item must still not be in attempted_ids
    next_challenge = get_next_unseen_challenge(seeded_db, session.id)
    assert next_challenge is not None
    assert next_challenge.id not in attempted_ids


def test_round_boundary_enforces_ten_items_per_round(seeded_db):
    """After 10 items in round 1, get_next_unseen_challenge returns None / signals round completion."""
    session = get_or_create_session(seeded_db, None)

    for i in range(10):
        challenge = get_next_unseen_challenge(seeded_db, session.id)
        assert challenge is not None, f"Expected challenge for attempt {i + 1}"
        record_attempt(
            db=seeded_db,
            session_id=session.id,
            challenge_id=challenge.id,
            selected_variant="A",
            time_taken_ms=800,
        )

    # 11th call must indicate round is complete
    over_limit_challenge = get_next_unseen_challenge(seeded_db, session.id)
    assert over_limit_challenge is None

    # Check session state
    seeded_db.refresh(session)
    assert session.status == "round_completed"


def test_double_attempt_rejection(seeded_db):
    """Attempting the same challenge twice in the same session must raise DuplicateAttemptError."""
    session = get_or_create_session(seeded_db, None)
    challenge = get_next_unseen_challenge(seeded_db, session.id)
    assert challenge is not None

    # First attempt succeeds
    record_attempt(
        db=seeded_db,
        session_id=session.id,
        challenge_id=challenge.id,
        selected_variant="A",
        time_taken_ms=1500,
    )

    # Second attempt for identical challenge must fail
    with pytest.raises(DuplicateAttemptError):
        record_attempt(
            db=seeded_db,
            session_id=session.id,
            challenge_id=challenge.id,
            selected_variant="B",
            time_taken_ms=1200,
        )


def test_attempt_after_round_completed_rejected(seeded_db):
    """Attempting a challenge after round threshold reached must raise RoundCompletedError."""
    session = get_or_create_session(seeded_db, None)
    challenges = seeded_db.query(Challenge).limit(11).all()

    for i in range(10):
        record_attempt(
            db=seeded_db,
            session_id=session.id,
            challenge_id=challenges[i].id,
            selected_variant="A",
            time_taken_ms=1000,
        )

    # Attempting 11th item in round 1
    with pytest.raises(RoundCompletedError):
        record_attempt(
            db=seeded_db,
            session_id=session.id,
            challenge_id=challenges[10].id,
            selected_variant="A",
            time_taken_ms=1000,
        )


def test_receipt_reveals_ground_truth_and_model_accuracy(seeded_db):
    """Receipt must reveal user correctness, true CTRs, p-value, and model comparisons with accuracy."""
    session = get_or_create_session(seeded_db, None)
    challenge = get_next_unseen_challenge(seeded_db, session.id)

    # Inspect challenge winning variant from DB
    target_challenge = seeded_db.query(Challenge).filter_by(id=challenge.id).first()
    correct_variant = target_challenge.winning_variant

    receipt = record_attempt(
        db=seeded_db,
        session_id=session.id,
        challenge_id=challenge.id,
        selected_variant=correct_variant,
        time_taken_ms=2100,
    )

    assert receipt.is_correct is True
    assert receipt.selected_variant == correct_variant
    assert receipt.winning_variant == correct_variant
    assert receipt.impressions_a == target_challenge.impressions_a
    assert receipt.impressions_b == target_challenge.impressions_b
    assert receipt.ctr_a == target_challenge.ctr_a
    assert receipt.ctr_b == target_challenge.ctr_b
    assert receipt.p_value == target_challenge.p_value
    assert receipt.round_number == 1
    assert receipt.attempt_index == 1
    assert receipt.round_items == 10

    # Verify model comparisons
    assert len(receipt.model_predictions) > 0
    for model_pred in receipt.model_predictions:
        assert hasattr(model_pred, "model_name")
        assert hasattr(model_pred, "predicted_variant")
        assert hasattr(model_pred, "is_model_correct")
        expected_model_correct = (
            model_pred.predicted_variant.upper() == target_challenge.winning_variant.upper()
        )
        assert model_pred.is_model_correct == expected_model_correct


# ---------------------------------------------------------------------------
# API Endpoint Integration Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_session_lifecycle(seeded_db):
    """Test session creation endpoint and current session status endpoint."""
    app.dependency_overrides[get_db] = lambda: seeded_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        res = await client.post("/api/sessions")
        assert res.status_code == 201
        session_data = res.json()
        assert "id" in session_data
        session_id = session_data["id"]
        assert session_data["current_round"] == 1
        assert session_data["status"] == "active"
        assert "humark_session_id" in res.cookies

        # Get current session info via header
        res_current = await client.get(
            "/api/sessions/current",
            headers={"X-Session-ID": session_id},
        )
        assert res_current.status_code == 200
        cur_data = res_current.json()
        assert cur_data["id"] == session_id
        assert cur_data["total_attempts"] == 0
        assert cur_data["round_attempts"] == 0

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_next_challenge_strictly_conceals_ground_truth(seeded_db):
    """GET /api/challenges/next must strictly conceal ground truth fields."""
    app.dependency_overrides[get_db] = lambda: seeded_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a session
        res_session = await client.post("/api/sessions")
        session_id = res_session.json()["id"]

        # Request next challenge
        res_challenge = await client.get(
            "/api/challenges/next",
            headers={"X-Session-ID": session_id},
        )
        assert res_challenge.status_code == 200
        challenge_data = res_challenge.json()

        # Must include public fields
        assert "id" in challenge_data
        assert "title" in challenge_data
        assert "thumbnail_a_url" in challenge_data
        assert "thumbnail_b_url" in challenge_data
        assert challenge_data["round_completed"] is False
        assert challenge_data["round_number"] == 1
        assert challenge_data["attempt_index"] == 1

        # Must NOT leak ground truth
        forbidden_fields = {
            "impressions_a",
            "clicks_a",
            "impressions_b",
            "clicks_b",
            "ctr_a",
            "ctr_b",
            "winning_variant",
            "z_score",
            "p_value",
            "provenance_source",
            "predictions",
        }
        for field in forbidden_fields:
            assert field not in challenge_data, f"Leaked forbidden field '{field}' in next challenge!"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_attempt_submission_and_receipt(seeded_db):
    """POST /api/challenges/{id}/attempt records choice and returns complete receipt."""
    app.dependency_overrides[get_db] = lambda: seeded_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        res_session = await client.post("/api/sessions")
        session_id = res_session.json()["id"]

        # Get next challenge
        res_next = await client.get(
            "/api/challenges/next",
            headers={"X-Session-ID": session_id},
        )
        challenge_id = res_next.json()["id"]

        # Submit attempt
        res_attempt = await client.post(
            f"/api/challenges/{challenge_id}/attempt",
            headers={"X-Session-ID": session_id},
            json={"selected_variant": "A", "time_taken_ms": 1450},
        )
        assert res_attempt.status_code == 200
        receipt = res_attempt.json()

        assert receipt["challenge_id"] == challenge_id
        assert receipt["selected_variant"] == "A"
        assert "is_correct" in receipt
        assert "winning_variant" in receipt
        assert "ctr_a" in receipt
        assert "ctr_b" in receipt
        assert "p_value" in receipt
        assert "model_predictions" in receipt
        assert len(receipt["model_predictions"]) > 0
        assert "is_model_correct" in receipt["model_predictions"][0]

        # Duplicate attempt for same challenge returns 409
        res_dup = await client.post(
            f"/api/challenges/{challenge_id}/attempt",
            headers={"X-Session-ID": session_id},
            json={"selected_variant": "B", "time_taken_ms": 1200},
        )
        assert res_dup.status_code == 409

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_round_completion_flow(seeded_db):
    """When a session completes 10 attempts, GET /api/challenges/next returns round_completed=true."""
    app.dependency_overrides[get_db] = lambda: seeded_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        res_session = await client.post("/api/sessions")
        session_id = res_session.json()["id"]

        for i in range(10):
            res_next = await client.get(
                "/api/challenges/next",
                headers={"X-Session-ID": session_id},
            )
            assert res_next.status_code == 200
            data = res_next.json()
            assert data["round_completed"] is False
            cid = data["id"]

            res_att = await client.post(
                f"/api/challenges/{cid}/attempt",
                headers={"X-Session-ID": session_id},
                json={"selected_variant": "A", "time_taken_ms": 900},
            )
            assert res_att.status_code == 200

        # 11th request: round must be marked completed
        res_11 = await client.get(
            "/api/challenges/next",
            headers={"X-Session-ID": session_id},
        )
        assert res_11.status_code == 200
        data_11 = res_11.json()
        assert data_11["round_completed"] is True
        assert data_11["round_number"] == 1

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_session_reset_forces_new_session(seeded_db):
    """Calling POST /api/sessions/reset unconditionally mints a fresh session."""
    app.dependency_overrides[get_db] = lambda: seeded_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create session and record an attempt
        res_session = await client.post("/api/sessions")
        assert res_session.status_code == 201
        old_session_id = res_session.json()["id"]

        res_next = await client.get(
            "/api/challenges/next",
            headers={"X-Session-ID": old_session_id},
        )
        assert res_next.status_code == 200
        challenge_id = res_next.json()["id"]

        res_attempt = await client.post(
            f"/api/challenges/{challenge_id}/attempt",
            headers={"X-Session-ID": old_session_id},
            json={"selected_variant": "A", "time_taken_ms": 1100},
        )
        assert res_attempt.status_code == 200

        # Verify old session has 1 attempt
        res_stats_old = await client.get(
            "/api/sessions/current",
            headers={"X-Session-ID": old_session_id},
        )
        assert res_stats_old.json()["total_attempts"] == 1

        # 2. Call POST /api/sessions/reset while passing old session's cookie and header
        res_reset = await client.post(
            "/api/sessions/reset",
            headers={
                "X-Session-ID": old_session_id,
                "Cookie": f"humark_session_id={old_session_id}",
            },
        )
        assert res_reset.status_code == 201
        reset_data = res_reset.json()
        new_session_id = reset_data["id"]

        # 3. Assertions
        assert new_session_id != old_session_id
        assert reset_data["total_attempts"] == 0
        assert reset_data["round_attempts"] == 0
        assert reset_data["current_round"] == 1
        assert res_reset.headers.get("X-Session-ID") == new_session_id

    app.dependency_overrides.clear()

