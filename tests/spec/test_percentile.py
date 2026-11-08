"""Contract and specification tests for human percentile ranking engine and bell curve coordinates."""

import math
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.percentile import (
    FRONTIER_AI_ACCURACY,
    HUMAN_BENCHMARK_MEAN,
    HUMAN_BENCHMARK_STD,
    TOP_2_PERCENT_THRESHOLD,
    PercentileBenchmark,
    calculate_human_percentile,
)
from app.core.scoring import calculate_session_scorecard
from app.db.base import Base
from app.db.session import get_db
from app.main import app


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


def test_percentile_constants():
    """Verify statistical constants anchored on WONO benchmark study."""
    assert HUMAN_BENCHMARK_MEAN == 0.528
    assert HUMAN_BENCHMARK_STD == 0.094
    assert FRONTIER_AI_ACCURACY == 0.750
    assert TOP_2_PERCENT_THRESHOLD == 0.722


def test_percentile_median_accuracy():
    """Human accuracy at exact benchmark mean (52.8%) should yield 50th percentile."""
    res = calculate_human_percentile(accuracy=0.528, total_attempts=10)
    assert isinstance(res, PercentileBenchmark)
    assert abs(res.z_score) < 0.01
    assert abs(res.percentile - 50.0) < 1.0
    assert res.is_top_2_percent is False
    assert res.beats_frontier_ai is False
    assert res.tier_label == "Median Human Baseline"


def test_percentile_frontier_ai_and_top_2_percent():
    """Accuracy at 75.0% and 80.0% should exceed 98th percentile and test threshold gates."""
    # 75.0% is exactly frontier AI accuracy (sitting at ~98.9th percentile)
    res_75 = calculate_human_percentile(accuracy=0.750, total_attempts=10)
    assert res_75.percentile >= 98.0
    assert res_75.is_top_2_percent is True
    assert res_75.beats_frontier_ai is False
    assert res_75.tier_label == "Top 2% Human Tier (Nearing Frontier AI)"

    # 80.0% out-performs frontier AI (75.0%)
    res_80 = calculate_human_percentile(accuracy=0.800, total_attempts=30)
    assert res_80.percentile >= 99.0
    assert res_80.is_top_2_percent is True
    assert res_80.beats_frontier_ai is True
    assert res_80.tier_label == "Top 2% Elite Evaluator (Outperforming Frontier AI)"


def test_percentile_tiers_and_clamping():
    """Test lower bounds, high performer tier, and percentile clamping between 0.1 and 99.9."""
    # Low score (40%) should yield <10th percentile and Calibration Tier
    res_low = calculate_human_percentile(accuracy=0.400, total_attempts=10)
    assert res_low.percentile < 10.0
    assert res_low.tier_label == "Calibration Tier"
    assert res_low.is_top_2_percent is False
    assert res_low.beats_frontier_ai is False

    # Extreme low (10%) clamped to 0.1
    res_extreme_low = calculate_human_percentile(accuracy=0.100, total_attempts=10)
    assert res_extreme_low.percentile == 0.1

    # Extreme high (100%) clamped to 99.9
    res_extreme_high = calculate_human_percentile(accuracy=1.000, total_attempts=30)
    assert res_extreme_high.percentile == 99.9
    assert res_extreme_high.beats_frontier_ai is True

    # High performer (70%)
    res_70 = calculate_human_percentile(accuracy=0.700, total_attempts=10)
    assert 70.0 <= res_70.percentile < 98.0
    assert res_70.tier_label == "High Performer (Above Average Human Intuition)"


def test_curve_coordinates_properties():
    """Verify the 25 curve points form a valid Gaussian distribution curve."""
    res = calculate_human_percentile(accuracy=0.600, total_attempts=10)
    points = res.curve_points
    assert len(points) == 25

    # Check monotonicity of x coordinates
    x_coords = [p[0] for p in points]
    assert x_coords[0] == pytest.approx(0.20, abs=1e-4)
    assert x_coords[-1] == pytest.approx(0.85, abs=1e-4)
    for i in range(len(x_coords) - 1):
        assert x_coords[i] < x_coords[i + 1]

    # Check bell shape: peak should be near HUMAN_BENCHMARK_MEAN (0.528)
    peak_pt = max(points, key=lambda p: p[1])
    assert abs(peak_pt[0] - 0.528) < 0.03

    # Check user_point and frontier_point coordinates
    ux, uy = res.user_point
    assert ux == pytest.approx(0.600, abs=1e-4)
    assert uy > 0.0

    fx, fy = res.frontier_point
    assert fx == pytest.approx(FRONTIER_AI_ACCURACY, abs=1e-4)
    assert fy > 0.0


@pytest.mark.asyncio
async def test_scorecard_percentile_integration(test_engine):
    """Verify calculate_session_scorecard and API response include percentile_benchmark."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    db = TestingSessionLocal()
    try:
        from app.core.game import get_or_create_session
        from app.models.challenge import Challenge
        from app.models.session import SessionAttempt

        session = get_or_create_session(db)

        # Ingest 10 dummy challenges
        challenges = []
        for i in range(10):
            ch = Challenge(
                id=f"test-percentile-ch-{i}",
                title=f"Test Thumbnail {i}",
                category="youtube_thumbnails",
                thumbnail_a_url=f"/test_a_{i}.jpg",
                thumbnail_b_url=f"/test_b_{i}.jpg",
                impressions_a=25000,
                clicks_a=2500,
                ctr_a=0.10,
                impressions_b=25000,
                clicks_b=1500,
                ctr_b=0.06,
                winning_variant="A",
                z_score=15.0,
                p_value=0.0001,
                provenance_source="test",
            )
            db.add(ch)
            challenges.append(ch)
        db.commit()

        # Add 10 attempts: 8 correct, 2 incorrect -> 80% accuracy
        for i in range(10):
            db.add(
                SessionAttempt(
                    session_id=session.id,
                    challenge_id=challenges[i].id,
                    round_number=1,
                    selected_variant="A" if i < 8 else "B",
                    is_correct=i < 8,
                    time_taken_ms=1200,
                )
            )
        db.commit()

        scorecard = calculate_session_scorecard(db, session.id)
        assert scorecard.percentile_benchmark is not None
        assert scorecard.percentile_benchmark.accuracy == 0.80
        assert scorecard.percentile_benchmark.is_top_2_percent is True
        assert scorecard.percentile_benchmark.beats_frontier_ai is True
        assert "Top 2% Elite Evaluator" in scorecard.percentile_benchmark.tier_label
        assert len(scorecard.percentile_benchmark.curve_points) == 25

        # Test through FastAPI client
        async def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/api/scorecard/{session.id}"
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "percentile_benchmark" in data
            pb = data["percentile_benchmark"]
            assert pb["percentile"] >= 98.0
            assert pb["beats_frontier_ai"] is True
            assert pb["tier_label"] == "Top 2% Elite Evaluator (Outperforming Frontier AI)"
            assert len(pb["curve_points"]) == 25
            assert "user_point" in pb
            assert "frontier_point" in pb
        app.dependency_overrides.clear()
    finally:
        db.close()

