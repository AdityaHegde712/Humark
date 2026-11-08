"""Contract and specification tests for visual motif tagging and failure-mode analysis engine.

Acceptance Criteria:
1. Seed challenges tagged with canonical visual motifs (face_emotion, curiosity_gap, text_contrast, visual_complexity).
2. calculate_motif_breakdown calculates user accuracy and frontier accuracy per motif on identical challenges.
3. Accuracy delta = user_accuracy - frontier_accuracy.
4. Verdict classification: human_dominant (delta > 0.05), ai_dominant (delta < -0.05), parity (-0.05 <= delta <= 0.05).
5. Partial runs only include motifs encountered so far.
6. Scorecard integration embeds motif_breakdown into ScorecardResponse.
"""

import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.game import get_or_create_session
from app.core.ingestion import ingest_batch
from app.core.motif_analysis import (
    CANONICAL_MOTIFS,
    calculate_motif_breakdown,
)
from app.core.scoring import calculate_session_scorecard
from app.db.base import Base
from app.eval.prompts import PROMPT_VERSION
from app.models.challenge import Challenge, ModelPrediction
from app.models.session import GameSession, SessionAttempt


@pytest.fixture
def test_engine():
    """Create an isolated in-memory SQLite database engine."""
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


def _create_challenge_with_motif(
    db,
    motif: str,
    winning_variant: str = "A",
    frontier_variant: str = "A",
) -> Challenge:
    """Helper to persist a challenge with a specified primary_motif and frontier prediction."""
    cid = str(uuid.uuid4())
    ch = Challenge(
        id=cid,
        title=f"Challenge for motif {motif}",
        category="youtube_thumbnails",
        primary_motif=motif,
        thumbnail_a_url="/static/thumbnails/test_a.svg",
        thumbnail_b_url="/static/thumbnails/test_b.svg",
        impressions_a=50000,
        clicks_a=5000 if winning_variant == "A" else 4000,
        ctr_a=0.10 if winning_variant == "A" else 0.08,
        impressions_b=50000,
        clicks_b=4000 if winning_variant == "A" else 5000,
        ctr_b=0.08 if winning_variant == "A" else 0.10,
        winning_variant=winning_variant,
        z_score=10.5,
        p_value=0.0001,
        provenance_source="Spec Test Bench",
        is_active=True,
    )
    db.add(ch)

    # Persist mock-frontier-v1 prediction
    pred = ModelPrediction(
        id=str(uuid.uuid4()),
        challenge_id=cid,
        model_name="mock-frontier-v1",
        model_version="1.0.0",
        predicted_variant=frontier_variant,
        confidence=0.85,
        reasoning="Test reasoning",
        prompt_version=PROMPT_VERSION,
        token_count=120,
        latency_ms=250,
        cost_usd=0.001,
    )
    db.add(pred)
    db.commit()
    db.refresh(ch)
    return ch


def test_empty_session_returns_empty_motif_breakdown(db_session):
    """Empty session with no attempts must return an empty list."""
    session = get_or_create_session(db_session)
    breakdown = calculate_motif_breakdown(db_session, session.id)
    assert breakdown == []


def test_partial_run_only_includes_encountered_motifs(db_session):
    """Sessions with attempts in only a subset of motifs must only return encountered motifs."""
    session = get_or_create_session(db_session)

    ch1 = _create_challenge_with_motif(db_session, motif="face_emotion", winning_variant="A", frontier_variant="A")
    ch2 = _create_challenge_with_motif(db_session, motif="face_emotion", winning_variant="B", frontier_variant="B")
    ch3 = _create_challenge_with_motif(db_session, motif="curiosity_gap", winning_variant="A", frontier_variant="A")

    # User attempts: 2 face_emotion (1 correct, 1 wrong), 1 curiosity_gap (1 correct)
    db_session.add(
        SessionAttempt(
            session_id=session.id,
            challenge_id=ch1.id,
            round_number=1,
            selected_variant="A",
            is_correct=True,
            time_taken_ms=1200,
        )
    )
    db_session.add(
        SessionAttempt(
            session_id=session.id,
            challenge_id=ch2.id,
            round_number=1,
            selected_variant="A",
            is_correct=False,
            time_taken_ms=1500,
        )
    )
    db_session.add(
        SessionAttempt(
            session_id=session.id,
            challenge_id=ch3.id,
            round_number=1,
            selected_variant="A",
            is_correct=True,
            time_taken_ms=1100,
        )
    )
    db_session.commit()

    breakdown = calculate_motif_breakdown(db_session, session.id)
    motifs_present = [item.motif for item in breakdown]

    assert "face_emotion" in motifs_present
    assert "curiosity_gap" in motifs_present
    assert "text_contrast" not in motifs_present
    assert "visual_complexity" not in motifs_present
    assert len(breakdown) == 2


def test_motif_accuracy_and_frontier_accuracy_computation(db_session):
    """Motif breakdown accurately computes user accuracy, frontier accuracy, and delta."""
    session = get_or_create_session(db_session)

    # Motif: face_emotion (User 100%, Frontier 0% -> Human Dominant)
    ch1 = _create_challenge_with_motif(db_session, "face_emotion", winning_variant="A", frontier_variant="B")
    ch2 = _create_challenge_with_motif(db_session, "face_emotion", winning_variant="B", frontier_variant="A")

    # User got both correct
    db_session.add(
        SessionAttempt(
            session_id=session.id,
            challenge_id=ch1.id,
            round_number=1,
            selected_variant="A",
            is_correct=True,
            time_taken_ms=1000,
        )
    )
    db_session.add(
        SessionAttempt(
            session_id=session.id,
            challenge_id=ch2.id,
            round_number=1,
            selected_variant="B",
            is_correct=True,
            time_taken_ms=1000,
        )
    )

    # Motif: text_contrast (User 0%, Frontier 100% -> AI Dominant)
    ch3 = _create_challenge_with_motif(db_session, "text_contrast", winning_variant="A", frontier_variant="A")
    db_session.add(
        SessionAttempt(
            session_id=session.id,
            challenge_id=ch3.id,
            round_number=1,
            selected_variant="B",
            is_correct=False,
            time_taken_ms=1000,
        )
    )

    # Motif: visual_complexity (User 100%, Frontier 100% -> Parity)
    ch4 = _create_challenge_with_motif(db_session, "visual_complexity", winning_variant="A", frontier_variant="A")
    db_session.add(
        SessionAttempt(
            session_id=session.id,
            challenge_id=ch4.id,
            round_number=1,
            selected_variant="A",
            is_correct=True,
            time_taken_ms=1000,
        )
    )
    db_session.commit()

    breakdown = calculate_motif_breakdown(db_session, session.id)
    by_motif = {b.motif: b for b in breakdown}

    # Verify face_emotion
    fe = by_motif["face_emotion"]
    assert fe.total_attempts == 2
    assert fe.user_correct == 2
    assert fe.user_accuracy == 1.0
    assert fe.frontier_accuracy == 0.0
    assert fe.accuracy_delta == 1.0
    assert fe.verdict == "human_dominant"
    assert "face" in fe.motif_name.lower() or "emotion" in fe.motif_name.lower()
    assert len(fe.insight) > 10

    # Verify text_contrast
    tc = by_motif["text_contrast"]
    assert tc.total_attempts == 1
    assert tc.user_correct == 0
    assert tc.user_accuracy == 0.0
    assert tc.frontier_accuracy == 1.0
    assert tc.accuracy_delta == -1.0
    assert tc.verdict == "ai_dominant"

    # Verify visual_complexity
    vc = by_motif["visual_complexity"]
    assert vc.total_attempts == 1
    assert vc.user_correct == 1
    assert vc.user_accuracy == 1.0
    assert vc.frontier_accuracy == 1.0
    assert vc.accuracy_delta == 0.0
    assert vc.verdict == "parity"


def test_verdict_threshold_boundaries(db_session):
    """Verdict classification correctly uses +0.05 and -0.05 thresholds."""
    session = get_or_create_session(db_session)

    # Test marginal parity: delta = +0.04 (within [-0.05, +0.05])
    # 25 items: user 13/25 = 0.52, frontier 12/25 = 0.48 -> delta = +0.04 -> parity
    # Create 25 challenges
    for i in range(25):
        w = "A" if i % 2 == 0 else "B"
        user_correct = i < 13
        user_sel = w if user_correct else ("B" if w == "A" else "A")
        front_correct = i < 12
        front_pred = w if front_correct else ("B" if w == "A" else "A")

        ch = _create_challenge_with_motif(
            db_session,
            motif="curiosity_gap",
            winning_variant=w,
            frontier_variant=front_pred,
        )
        db_session.add(
            SessionAttempt(
                session_id=session.id,
                challenge_id=ch.id,
                round_number=1,
                selected_variant=user_sel,
                is_correct=user_correct,
                time_taken_ms=1000,
            )
        )
    db_session.commit()

    breakdown = calculate_motif_breakdown(db_session, session.id)
    cg = breakdown[0]
    assert cg.user_accuracy == 0.52
    assert cg.frontier_accuracy == 0.48
    assert cg.accuracy_delta == 0.04
    assert cg.verdict == "parity"


def test_scorecard_response_includes_motif_breakdown(db_session):
    """calculate_session_scorecard includes populated motif_breakdown."""
    session = get_or_create_session(db_session)
    ch = _create_challenge_with_motif(db_session, "face_emotion", winning_variant="A", frontier_variant="A")

    db_session.add(
        SessionAttempt(
            session_id=session.id,
            challenge_id=ch.id,
            round_number=1,
            selected_variant="A",
            is_correct=True,
            time_taken_ms=1200,
        )
    )
    db_session.commit()

    scorecard = calculate_session_scorecard(db_session, session.id)
    assert hasattr(scorecard, "motif_breakdown")
    assert len(scorecard.motif_breakdown) == 1
    assert scorecard.motif_breakdown[0].motif == "face_emotion"
