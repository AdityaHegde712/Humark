"""End-to-End Integration Test Suite for Humark 3-Round Benchmark Gameplay.

Covers:
1. Seed database state verification (36 challenges, pre-computed baseline predictions).
2. Fresh guest player session creation via POST /api/sessions.
3. Round 1 gameplay (10 items):
   - Verifies public challenge schema strictly hides ground truth.
   - Submits decisions, asserts immediate receipts with ground truth CTRs, p-value (<0.05),
     and 3 baseline model predictions (mock-frontier-v1, mock-compact-v1, mock-heuristic-v1).
   - Verifies 11th request signals round_completed=True.
4. Scorecard verification post Round 1:
   - Verifies accuracy, Wilson 95% confidence interval, sample size warning (n < 30),
     and head-to-head model comparisons.
5. Round 2 progression and unseen item selection:
   - Verifies zero repeat challenges between Round 1 and Round 2.
6. Round 3 progression and benchmark completion:
   - Verifies strictly 30 unique challenges played across the entire session.
7. Anti-luck verification threshold evaluation:
   - Score >= 22/30 (e.g. 24/30) achieves is_verified=True.
   - Tamper-evident SHA-256 verification digest in VerificationAuditLog.
   - Scorecard sample size warning clears (n=30).
8. Failing verification track simulation:
   - Simulates second player achieving < 22/30 (e.g. 15/30).
   - Verifies is_verified=False and session status="failed".
"""

import pytest
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.challenge import Challenge, ModelPrediction
from app.models.session import GameSession
from app.models.verification import VerificationAuditLog
from app.scripts.seed import seed_challenges_data
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

SENSITIVE_GROUND_TRUTH_KEYS = {
    "winning_variant",
    "ctr_a",
    "ctr_b",
    "clicks_a",
    "clicks_b",
    "impressions_a",
    "impressions_b",
    "z_score",
    "p_value",
}

EXPECTED_BASELINE_MODELS = {
    "mock-frontier-v1",
    "mock-compact-v1",
    "mock-heuristic-v1",
}


@pytest.fixture
def e2e_db():
    """Create an isolated database seeded with the standard benchmark challenge catalog."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    db = TestingSessionLocal()

    # Ingest benchmark seed catalog and precompute baselines
    seed_result = seed_challenges_data(db)
    assert seed_result == 0, "Seed ingestion failed for e2e_db"

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield db

    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.mark.asyncio
async def test_end_to_end_gameplay_and_verification_flow(e2e_db):
    """Execute complete 3-round gameplay integration test for successful and failing players."""
    # -------------------------------------------------------------------------
    # 1. Verify database has 36 seed challenges with pre-computed baseline predictions
    # -------------------------------------------------------------------------
    challenges_count = e2e_db.query(Challenge).count()
    assert challenges_count == 36, f"Expected 36 challenges, found {challenges_count}"

    predictions_count = e2e_db.query(ModelPrediction).count()
    assert predictions_count == 108, f"Expected 108 predictions (36 * 3), found {predictions_count}"

    all_challenges = e2e_db.query(Challenge).all()
    for ch in all_challenges:
        preds = e2e_db.query(ModelPrediction).filter_by(challenge_id=ch.id).all()
        model_names = {p.model_name for p in preds}
        assert model_names == EXPECTED_BASELINE_MODELS, f"Challenge {ch.id} missing baseline models"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # -------------------------------------------------------------------------
        # 2. Initialize guest session via POST /api/sessions (Player 1)
        # -------------------------------------------------------------------------
        create_res = await client.post("/api/sessions")
        assert create_res.status_code == 201
        session_data = create_res.json()
        session_id_1 = session_data["id"]
        assert session_id_1 is not None
        assert create_res.headers.get("X-Session-ID") == session_id_1

        headers_p1 = {"X-Session-ID": session_id_1}

        # -------------------------------------------------------------------------
        # 3. Plays Round 1 (10 challenges)
        # -------------------------------------------------------------------------
        round_1_challenges: list[str] = []

        for item_idx in range(1, 11):
            next_res = await client.get("/api/challenges/next", headers=headers_p1)
            assert next_res.status_code == 200
            next_data = next_res.json()

            # Validate public schema hides ground truth
            for key in SENSITIVE_GROUND_TRUTH_KEYS:
                assert key not in next_data, f"Ground truth '{key}' leaked in public challenge schema!"

            assert next_data["round_completed"] is False
            assert next_data["round_number"] == 1
            assert next_data["attempt_index"] == item_idx
            assert next_data["total_round_items"] == 10
            assert next_data["id"] is not None

            ch_id = next_data["id"]
            round_1_challenges.append(ch_id)

            # Strategy for Player 1: 8 correct, 2 incorrect per round (total 24/30 = 80%)
            challenge_obj = e2e_db.query(Challenge).filter_by(id=ch_id).first()
            assert challenge_obj is not None
            should_be_correct = item_idx <= 8
            if should_be_correct:
                chosen_variant = challenge_obj.winning_variant
            else:
                chosen_variant = "B" if challenge_obj.winning_variant == "A" else "A"

            # Submit attempt
            attempt_res = await client.post(
                f"/api/challenges/{ch_id}/attempt",
                json={"selected_variant": chosen_variant, "time_taken_ms": 1100 + item_idx * 50},
                headers=headers_p1,
            )
            assert attempt_res.status_code == 200
            receipt = attempt_res.json()

            # Immediate receipt assertions
            assert receipt["is_correct"] is should_be_correct
            assert receipt["winning_variant"] == challenge_obj.winning_variant
            assert receipt["winning_variant"] in ("A", "B")
            assert receipt["ctr_a"] == challenge_obj.ctr_a
            assert receipt["ctr_b"] == challenge_obj.ctr_b
            assert receipt["p_value"] < 0.05
            assert receipt["impressions_a"] >= 20000
            assert receipt["impressions_b"] >= 20000

            # Baseline model assertions
            receipt_models = {p["model_name"] for p in receipt["model_predictions"]}
            assert receipt_models == EXPECTED_BASELINE_MODELS
            for p in receipt["model_predictions"]:
                assert p["predicted_variant"] in ("A", "B")
                assert 0.0 <= p["confidence"] <= 1.0
                assert isinstance(p["is_model_correct"], bool)
                assert len(p["reasoning"]) > 0

        # Verify 11th request signals round_completed: true
        r1_over_res = await client.get("/api/challenges/next", headers=headers_p1)
        assert r1_over_res.status_code == 200
        assert r1_over_res.json()["round_completed"] is True
        assert r1_over_res.json()["id"] is None

        # -------------------------------------------------------------------------
        # 4. Retrieves Round 1 Scorecard (GET /api/scorecard)
        # -------------------------------------------------------------------------
        sc_res = await client.get("/api/scorecard", headers=headers_p1)
        assert sc_res.status_code == 200
        sc = sc_res.json()

        assert sc["session_id"] == session_id_1
        assert sc["total_attempts"] == 10
        assert sc["correct_attempts"] == 8
        assert sc["accuracy"] == 0.8
        assert sc["current_round"] == 1
        assert sc["rounds_completed"] == 1
        assert sc["wilson_interval"]["sample_size_warning"] is True  # 10 < 30
        assert 0.0 <= sc["wilson_interval"]["lower"] <= sc["wilson_interval"]["upper"] <= 1.0

        # Head-to-head model comparison
        comparisons = sc["model_comparisons"]
        assert len(comparisons) == 3
        for comp in comparisons:
            assert comp["model_name"] in EXPECTED_BASELINE_MODELS
            assert comp["user_beat_model"] >= 0
            assert comp["model_beat_user"] >= 0
            assert comp["ties"] >= 0
            assert comp["user_beat_model"] + comp["model_beat_user"] + comp["ties"] == 10
            assert comp["verdict"] in ("ahead", "behind", "tied")

        # -------------------------------------------------------------------------
        # 5. Advances to Round 2 (POST /api/sessions/advance-round)
        # -------------------------------------------------------------------------
        adv_res_2 = await client.post("/api/sessions/advance-round", headers=headers_p1)
        assert adv_res_2.status_code == 200
        assert adv_res_2.json()["current_round"] == 2

        round_2_challenges: list[str] = []
        for item_idx in range(1, 11):
            next_res = await client.get("/api/challenges/next", headers=headers_p1)
            assert next_res.status_code == 200
            next_data = next_res.json()

            ch_id = next_data["id"]
            assert ch_id is not None
            assert ch_id not in round_1_challenges, f"Challenge {ch_id} repeated from Round 1!"
            round_2_challenges.append(ch_id)

            challenge_obj = e2e_db.query(Challenge).filter_by(id=ch_id).first()
            assert challenge_obj is not None
            should_be_correct = item_idx <= 8
            chosen_variant = (
                challenge_obj.winning_variant
                if should_be_correct
                else ("B" if challenge_obj.winning_variant == "A" else "A")
            )

            attempt_res = await client.post(
                f"/api/challenges/{ch_id}/attempt",
                json={"selected_variant": chosen_variant, "time_taken_ms": 1200},
                headers=headers_p1,
            )
            assert attempt_res.status_code == 200

        # Verify zero repeats between Round 1 and Round 2
        assert len(round_2_challenges) == 10
        assert len(set(round_1_challenges).intersection(set(round_2_challenges))) == 0

        # 11th request in Round 2 signals round_completed: true
        r2_over_res = await client.get("/api/challenges/next", headers=headers_p1)
        assert r2_over_res.status_code == 200
        assert r2_over_res.json()["round_completed"] is True

        # -------------------------------------------------------------------------
        # 6. Advances to Round 3 (POST /api/sessions/advance-round)
        # -------------------------------------------------------------------------
        adv_res_3 = await client.post("/api/sessions/advance-round", headers=headers_p1)
        assert adv_res_3.status_code == 200
        assert adv_res_3.json()["current_round"] == 3

        round_3_challenges: list[str] = []
        for item_idx in range(1, 11):
            next_res = await client.get("/api/challenges/next", headers=headers_p1)
            assert next_res.status_code == 200
            next_data = next_res.json()

            ch_id = next_data["id"]
            assert ch_id is not None
            assert ch_id not in round_1_challenges, f"Challenge {ch_id} repeated from Round 1!"
            assert ch_id not in round_2_challenges, f"Challenge {ch_id} repeated from Round 2!"
            round_3_challenges.append(ch_id)

            challenge_obj = e2e_db.query(Challenge).filter_by(id=ch_id).first()
            assert challenge_obj is not None
            should_be_correct = item_idx <= 8
            chosen_variant = (
                challenge_obj.winning_variant
                if should_be_correct
                else ("B" if challenge_obj.winning_variant == "A" else "A")
            )

            attempt_res = await client.post(
                f"/api/challenges/{ch_id}/attempt",
                json={"selected_variant": chosen_variant, "time_taken_ms": 1200},
                headers=headers_p1,
            )
            assert attempt_res.status_code == 200

        # Verify strictly 30 unique challenges played across the entire session
        all_played = round_1_challenges + round_2_challenges + round_3_challenges
        assert len(all_played) == 30
        assert len(set(all_played)) == 30, "Found duplicate challenges across rounds in session!"

        # 11th request in Round 3 signals round_completed: true
        r3_over_res = await client.get("/api/challenges/next", headers=headers_p1)
        assert r3_over_res.status_code == 200
        assert r3_over_res.json()["round_completed"] is True

        # -------------------------------------------------------------------------
        # 7. Verifies Anti-Luck Verification Result (Player 1 achieved 24/30 >= 22)
        # -------------------------------------------------------------------------
        ver_res = await client.get("/api/sessions/verification", headers=headers_p1)
        assert ver_res.status_code == 200
        ver_data = ver_res.json()

        assert ver_data["is_completed"] is True
        assert ver_data["is_verified"] is True
        assert ver_data["status"] == "verified"
        assert ver_data["total_attempts"] == 30
        assert ver_data["cumulative_accuracy"] == 0.8
        assert ver_data["round_scores"]["round_1"] == 8
        assert ver_data["round_scores"]["round_2"] == 8
        assert ver_data["round_scores"]["round_3"] == 8

        verification_hash = ver_data["verification_hash"]
        assert verification_hash is not None
        assert len(verification_hash) == 64
        assert all(c in "0123456789abcdef" for c in verification_hash)

        # Database audit log assertions
        audit_log = (
            e2e_db.query(VerificationAuditLog)
            .filter_by(session_id=session_id_1)
            .first()
        )
        assert audit_log is not None
        assert audit_log.is_verified is True
        assert audit_log.total_attempts == 30
        assert audit_log.correct_attempts == 24
        assert audit_log.verification_hash == verification_hash

        # Scorecard assertions post complete verification track
        final_sc_res = await client.get("/api/scorecard", headers=headers_p1)
        assert final_sc_res.status_code == 200
        final_sc = final_sc_res.json()

        assert final_sc["total_attempts"] == 30
        assert final_sc["correct_attempts"] == 24
        assert final_sc["accuracy"] == 0.8
        assert final_sc["is_verified"] is True
        assert final_sc["rounds_completed"] == 3
        assert final_sc["wilson_interval"]["sample_size_warning"] is False  # Sufficient sample n=30

        # -------------------------------------------------------------------------
        # 8. Simulate second player scoring < 22/30 (e.g. 15 correct: 5 per round)
        # -------------------------------------------------------------------------
        # A separate client instance simulates a distinct visitor browser without existing cookies
        async with AsyncClient(transport=transport, base_url="http://test") as client2:
            p2_create_res = await client2.post("/api/sessions")
            assert p2_create_res.status_code == 201
            session_id_2 = p2_create_res.json()["id"]
            assert session_id_2 != session_id_1

            headers_p2 = {"X-Session-ID": session_id_2}

            for r in range(1, 4):
                for item_idx in range(1, 11):
                    next_res = await client2.get("/api/challenges/next", headers=headers_p2)
                    assert next_res.status_code == 200
                    ch_id = next_res.json()["id"]
                    assert ch_id is not None

                    challenge_obj = e2e_db.query(Challenge).filter_by(id=ch_id).first()
                    assert challenge_obj is not None

                    # Player 2 scores 5 correct, 5 incorrect per round (total 15/30 = 50%)
                    should_be_correct = item_idx <= 5
                    chosen_variant = (
                        challenge_obj.winning_variant
                        if should_be_correct
                        else ("B" if challenge_obj.winning_variant == "A" else "A")
                    )

                    attempt_res = await client2.post(
                        f"/api/challenges/{ch_id}/attempt",
                        json={"selected_variant": chosen_variant, "time_taken_ms": 1300},
                        headers=headers_p2,
                    )
                    assert attempt_res.status_code == 200

                if r < 3:
                    adv_res = await client2.post("/api/sessions/advance-round", headers=headers_p2)
                    assert adv_res.status_code == 200

            # Player 2 verification check: failed
            p2_ver_res = await client2.get("/api/sessions/verification", headers=headers_p2)
            assert p2_ver_res.status_code == 200
            p2_ver_data = p2_ver_res.json()

            assert p2_ver_data["is_completed"] is True
            assert p2_ver_data["is_verified"] is False
            assert p2_ver_data["status"] == "failed"
            assert p2_ver_data["total_attempts"] == 30
            assert p2_ver_data["cumulative_accuracy"] == 0.5
            assert p2_ver_data["round_scores"]["round_1"] == 5
            assert p2_ver_data["round_scores"]["round_2"] == 5
            assert p2_ver_data["round_scores"]["round_3"] == 5

            # Player 2 scorecard check
            p2_sc_res = await client2.get("/api/scorecard", headers=headers_p2)
            assert p2_sc_res.status_code == 200
            p2_sc = p2_sc_res.json()

            assert p2_sc["is_verified"] is False
            assert p2_sc["status"] == "failed"
            assert p2_sc["total_attempts"] == 30
            assert p2_sc["correct_attempts"] == 15
            assert p2_sc["accuracy"] == 0.5
            assert p2_sc["wilson_interval"]["sample_size_warning"] is False

            # Database session and audit verification for Player 2
            p2_session = e2e_db.query(GameSession).filter_by(id=session_id_2).first()
            assert p2_session.status == "failed"

            p2_audit = (
                e2e_db.query(VerificationAuditLog)
                .filter_by(session_id=session_id_2)
                .first()
            )
            assert p2_audit is not None
            assert p2_audit.is_verified is False
            assert p2_audit.correct_attempts == 15
