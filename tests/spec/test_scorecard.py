"""Contract and specification tests for scorecard engine and telemetry.

Tests verify:
1. Empty session scorecard: 0 attempts, sample_size_warning=True, accuracy=0.0.
2. 10 attempts (Round 1): accuracy=70%, Wilson interval verified, head-to-head comparison
   correctly counts beats/losses/ties against all 3 mock baseline models.
3. 30 attempts (Round 3): sample_size_warning=False, verified status and tamper-evident audit hash included.
4. 30 attempts unverified: accurate status and verification hash generated.
5. SessionNotFoundError on nonexistent session IDs.
6. API endpoint GET /api/scorecard with header and cookie authentication.
7. API endpoint GET /api/scorecard/{session_id} shareable public lookup.
8. API error handling (401 Unauthorized for missing session, 404 Not Found for missing session).
"""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.game import get_or_create_session
from app.core.ingestion import ingest_batch
from app.core.scoring import (
    SessionNotFoundError,
    calculate_session_scorecard,
)
from app.core.verification import advance_round, evaluate_verification
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.challenge import Challenge
from app.models.session import SessionAttempt


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
    """Seed database with 35 valid challenges with precomputed baseline model predictions."""
    challenges = []
    for i in range(1, 36):
        win_var = "A" if i % 2 == 1 else "B"
        clicks_a = 4000 if win_var == "A" else 3000
        clicks_b = 3000 if win_var == "A" else 4000
        challenges.append(
            {
                "id": f"c{i:04d}0000-0000-0000-0000-000000000000",
                "title": f"Scorecard Challenge {i:02d}",
                "category": "youtube_thumbnails",
                "thumbnail_a_url": f"/static/thumbnails/challenge_{i:02d}_a.svg",
                "thumbnail_b_url": f"/static/thumbnails/challenge_{i:02d}_b.svg",
                "impressions_a": 50000,
                "clicks_a": clicks_a,
                "impressions_b": 50000,
                "clicks_b": clicks_b,
                "provenance_source": f"Scorecard Channel {i}",
            }
        )
    ingest_batch(challenges, db_session, precompute_baselines=True)
    return db_session


def populate_round_attempts(
    db,
    session_id: str,
    round_number: int,
    total_items: int = 10,
    correct_count: int = 7,
):
    """Helper to populate attempts for a given round with deterministic correctness."""
    challenges = (
        db.query(Challenge)
        .order_by(Challenge.id.asc())
        .offset((round_number - 1) * 10)
        .limit(total_items)
        .all()
    )

    for idx, ch in enumerate(challenges):
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
            time_taken_ms=1000 + idx * 100,
        )
        db.add(attempt)
    db.commit()


# ---------------------------------------------------------------------------
# Core Scoring Engine Unit Tests
# ---------------------------------------------------------------------------


def test_scorecard_empty_session(seeded_db_30):
    """Empty session must return 0 attempts, sample_size_warning=True, accuracy=0.0."""
    session = get_or_create_session(seeded_db_30)

    scorecard = calculate_session_scorecard(seeded_db_30, session.id)

    assert scorecard.session_id == session.id
    assert scorecard.total_attempts == 0
    assert scorecard.correct_attempts == 0
    assert scorecard.accuracy == 0.0
    assert scorecard.average_time_taken_ms == 0.0
    assert scorecard.current_round == 1
    assert scorecard.rounds_completed == 0
    assert scorecard.status == "active"
    assert scorecard.is_verified is False
    assert scorecard.wilson_interval.sample_size_warning is True
    assert scorecard.wilson_interval.lower == 0.0
    assert scorecard.wilson_interval.upper == 1.0
    assert scorecard.model_comparisons == []
    assert scorecard.category_breakdown == []
    assert scorecard.verification_hash is None
    assert scorecard.verification_audit is None


def test_scorecard_round_1_ten_attempts(seeded_db_30):
    """Round 1 with 10 attempts: accuracy=70%, Wilson warning=True, model comparisons computed."""
    session = get_or_create_session(seeded_db_30)
    populate_round_attempts(
        seeded_db_30, session.id, round_number=1, total_items=10, correct_count=7
    )

    scorecard = calculate_session_scorecard(seeded_db_30, session.id)

    assert scorecard.session_id == session.id
    assert scorecard.total_attempts == 10
    assert scorecard.correct_attempts == 7
    assert scorecard.accuracy == 0.7
    assert scorecard.average_time_taken_ms == pytest.approx(1450.0, rel=1e-2)
    assert scorecard.rounds_completed == 1
    assert scorecard.is_verified is False

    # Wilson interval check
    assert scorecard.wilson_interval.sample_size_warning is True
    assert 0.0 < scorecard.wilson_interval.lower < 0.7
    assert 0.7 < scorecard.wilson_interval.upper <= 1.0

    # Model comparisons check
    assert len(scorecard.model_comparisons) == 3
    model_names = [m.model_name for m in scorecard.model_comparisons]
    assert "mock-frontier-v1" in model_names
    assert "mock-compact-v1" in model_names
    assert "mock-heuristic-v1" in model_names
    assert sorted(scorecard.available_models) == sorted(model_names)

    for comp in scorecard.model_comparisons:
        # Beats + losses + ties must equal 10
        assert comp.user_beat_model + comp.model_beat_user + comp.ties == 10
        assert 0.0 <= comp.model_accuracy <= 1.0
        assert comp.accuracy_delta == pytest.approx(0.7 - comp.model_accuracy, abs=1e-4)
        if comp.accuracy_delta > 0:
            assert comp.verdict == "ahead"
        elif comp.accuracy_delta < 0:
            assert comp.verdict == "behind"
        else:
            assert comp.verdict == "tied"

    # Category breakdown check
    assert len(scorecard.category_breakdown) == 1
    cat = scorecard.category_breakdown[0]
    assert cat.category == "youtube_thumbnails"
    assert cat.total_attempts == 10
    assert cat.correct_attempts == 7
    assert cat.accuracy == 0.7


def test_scorecard_round_3_thirty_attempts_verified(seeded_db_30):
    """Round 3 with 30 attempts and >70% accuracy: sample_size_warning=False, verified=True with hash."""
    session = get_or_create_session(seeded_db_30)

    # Round 1: 8/10
    populate_round_attempts(
        seeded_db_30, session.id, round_number=1, total_items=10, correct_count=8
    )
    advance_round(seeded_db_30, session.id)

    # Round 2: 8/10
    populate_round_attempts(
        seeded_db_30, session.id, round_number=2, total_items=10, correct_count=8
    )
    advance_round(seeded_db_30, session.id)

    # Round 3: 7/10 (Total: 23/30 = 76.67% > 70%)
    populate_round_attempts(
        seeded_db_30, session.id, round_number=3, total_items=10, correct_count=7
    )

    # Evaluate verification
    eval_result = evaluate_verification(seeded_db_30, session.id)
    assert eval_result.is_verified is True

    scorecard = calculate_session_scorecard(seeded_db_30, session.id)

    assert scorecard.session_id == session.id
    assert scorecard.total_attempts == 30
    assert scorecard.correct_attempts == 23
    assert scorecard.accuracy == pytest.approx(23 / 30, rel=1e-4)
    assert scorecard.rounds_completed == 3
    assert scorecard.is_verified is True
    assert scorecard.status == "verified"
    assert scorecard.wilson_interval.sample_size_warning is False
    assert scorecard.wilson_interval.lower > 0.5
    assert scorecard.verification_hash is not None
    assert len(scorecard.verification_hash) == 64
    assert scorecard.verification_audit is not None
    assert scorecard.verification_audit.round_1_correct == 8
    assert scorecard.verification_audit.round_2_correct == 8
    assert scorecard.verification_audit.round_3_correct == 7
    assert (
        scorecard.verification_audit.verification_hash == eval_result.verification_hash
    )

    # Model comparisons across all 30 items
    assert len(scorecard.model_comparisons) == 3
    for comp in scorecard.model_comparisons:
        assert comp.user_beat_model + comp.model_beat_user + comp.ties == 30


def test_scorecard_round_3_unverified(seeded_db_30):
    """Round 3 with 30 attempts but <= 70% accuracy: is_verified=False, hash generated."""
    session = get_or_create_session(seeded_db_30)

    # Total 18/30 (60% <= 70%)
    populate_round_attempts(
        seeded_db_30, session.id, round_number=1, total_items=10, correct_count=6
    )
    advance_round(seeded_db_30, session.id)

    populate_round_attempts(
        seeded_db_30, session.id, round_number=2, total_items=10, correct_count=6
    )
    advance_round(seeded_db_30, session.id)

    populate_round_attempts(
        seeded_db_30, session.id, round_number=3, total_items=10, correct_count=6
    )

    eval_result = evaluate_verification(seeded_db_30, session.id)
    assert eval_result.is_verified is False

    scorecard = calculate_session_scorecard(seeded_db_30, session.id)

    assert scorecard.total_attempts == 30
    assert scorecard.correct_attempts == 18
    assert scorecard.is_verified is False
    assert scorecard.status == "failed"
    assert scorecard.wilson_interval.sample_size_warning is False
    assert scorecard.verification_hash is not None
    assert scorecard.verification_audit is not None


def test_scorecard_session_not_found(seeded_db_30):
    """calculate_session_scorecard must raise SessionNotFoundError for nonexistent session."""
    with pytest.raises(SessionNotFoundError) as exc_info:
        calculate_session_scorecard(seeded_db_30, "nonexistent-session-id")
    assert "not found" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# API Integration Tests (GET /api/scorecard & GET /api/scorecard/{session_id})
# ---------------------------------------------------------------------------


@pytest.fixture
def test_client(db_session, test_engine):
    """Create an AsyncClient with database session dependency overridden."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_api_get_scorecard_unauthorized_when_missing_session(test_client):
    """GET /api/scorecard without session ID header/cookie returns HTTP 401."""
    response = await test_client.get("/api/scorecard")
    assert response.status_code == 401
    assert "Session ID required" in response.json()["detail"]


@pytest.mark.anyio
async def test_api_get_scorecard_not_found(test_client):
    """GET /api/scorecard with invalid session header returns HTTP 404."""
    response = await test_client.get(
        "/api/scorecard",
        headers={"X-Session-ID": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_api_get_scorecard_current_with_header(seeded_db_30, test_client):
    """GET /api/scorecard with X-Session-ID header returns current session scorecard."""
    session = get_or_create_session(seeded_db_30)
    populate_round_attempts(
        seeded_db_30, session.id, round_number=1, total_items=10, correct_count=7
    )

    response = await test_client.get(
        "/api/scorecard",
        headers={"X-Session-ID": session.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session.id
    assert data["total_attempts"] == 10
    assert data["correct_attempts"] == 7
    assert data["accuracy"] == 0.7
    assert data["wilson_interval"]["sample_size_warning"] is True
    assert len(data["model_comparisons"]) == 3


@pytest.mark.anyio
async def test_api_get_scorecard_current_with_cookie(seeded_db_30, test_client):
    """GET /api/scorecard with humark_session_id cookie returns current session scorecard."""
    session = get_or_create_session(seeded_db_30)
    populate_round_attempts(
        seeded_db_30, session.id, round_number=1, total_items=10, correct_count=8
    )

    response = await test_client.get(
        "/api/scorecard",
        headers={"Cookie": f"humark_session_id={session.id}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session.id
    assert data["total_attempts"] == 10
    assert data["correct_attempts"] == 8


@pytest.mark.anyio
async def test_api_get_scorecard_by_session_id_matches(seeded_db_30, test_client):
    """GET /api/scorecard/{session_id} returns identical public scorecard payload."""
    session = get_or_create_session(seeded_db_30)
    populate_round_attempts(
        seeded_db_30, session.id, round_number=1, total_items=10, correct_count=7
    )

    res_auth = await test_client.get(
        "/api/scorecard",
        headers={"X-Session-ID": session.id},
    )
    assert res_auth.status_code == 200

    res_public = await test_client.get(f"/api/scorecard/{session.id}")
    assert res_public.status_code == 200
    assert res_public.json() == res_auth.json()


@pytest.mark.anyio
async def test_api_get_scorecard_by_session_id_not_found(test_client):
    """GET /api/scorecard/{session_id} returns HTTP 404 for unknown session ID."""
    response = await test_client.get("/api/scorecard/nonexistent-uuid")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
