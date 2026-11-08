"""Contract and integration tests for challenge models and data ingestion pipeline.

Verifies:
1. Statistical significance hard gate enforcement during ingestion.
2. Provenance source requirement enforcement.
3. Automated calculation of CTRs, winning variant, z-score, and p-value.
4. Data model persistence with SQLite and PostgreSQL compatibility.
5. Strict information hiding: ChallengePublic schema never leaks ground truth.
6. ChallengeReceipt reveals ground truth and model predictions.
7. Admin ingestion API endpoint behavior and summary reporting.
8. Seed challenges integrity (36 items, all passing significance gate).
"""

import json
from pathlib import Path

import pytest
from app.core.ingestion import (
    IngestionError,
    ingest_batch,
    ingest_challenge_item,
)
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.challenge import Challenge, ModelPrediction
from app.schemas.challenge import (
    ChallengePublic,
    ChallengeReceipt,
)
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def valid_challenge_payload() -> dict:
    """Fixture providing a statistically valid challenge payload."""
    return {
        "id": "c1000000-0000-0000-0000-000000000001",
        "title": "Face vs Product Focus in Tech Review",
        "category": "youtube_thumbnails",
        "thumbnail_a_url": "/static/thumbnails/challenge_01_a.svg",
        "thumbnail_b_url": "/static/thumbnails/challenge_01_b.svg",
        "impressions_a": 50000,
        "clicks_a": 4200,  # CTR = 8.4%
        "impressions_b": 50000,
        "clicks_b": 3500,  # CTR = 7.0%
        "provenance_source": "TechChannel A/B Test 2024 (DEMO DATA)",
    }


def test_ingestion_rejects_insufficient_impressions(db_session):
    """Ingestion must reject challenges where either variant has N < 20,000."""
    invalid_payload = {
        "title": "Low Traffic Experiment",
        "category": "youtube_thumbnails",
        "thumbnail_a_url": "/static/thumbnails/low_a.svg",
        "thumbnail_b_url": "/static/thumbnails/low_b.svg",
        "impressions_a": 15000,  # Below 20,000 threshold
        "clicks_a": 1500,
        "impressions_b": 25000,
        "clicks_b": 2000,
        "provenance_source": "Channel A/B Test (DEMO DATA)",
    }

    with pytest.raises(IngestionError) as exc_info:
        ingest_challenge_item(invalid_payload, db_session)

    assert "Insufficient impressions" in str(exc_info.value)
    assert db_session.query(Challenge).count() == 0


def test_ingestion_rejects_insignificant_difference(db_session):
    """Ingestion must reject challenges where difference is not significant (p >= 0.05)."""
    insignificant_payload = {
        "title": "Insignificant Variation",
        "category": "youtube_thumbnails",
        "thumbnail_a_url": "/static/thumbnails/test_a.svg",
        "thumbnail_b_url": "/static/thumbnails/test_b.svg",
        "impressions_a": 30000,
        "clicks_a": 2100,  # CTR = 7.00%
        "impressions_b": 30000,
        "clicks_b": 2105,  # CTR = 7.017% (p > 0.05)
        "provenance_source": "Channel Test (DEMO DATA)",
    }

    with pytest.raises(IngestionError) as exc_info:
        ingest_challenge_item(insignificant_payload, db_session)

    assert "Statistically insignificant difference" in str(exc_info.value)
    assert db_session.query(Challenge).count() == 0


def test_ingestion_rejects_missing_or_empty_provenance(db_session):
    """Ingestion must reject items missing provenance metadata."""
    payload = {
        "title": "No Provenance Challenge",
        "category": "youtube_thumbnails",
        "thumbnail_a_url": "/static/thumbnails/a.svg",
        "thumbnail_b_url": "/static/thumbnails/b.svg",
        "impressions_a": 50000,
        "clicks_a": 4000,
        "impressions_b": 50000,
        "clicks_b": 3000,
        "provenance_source": "   ",  # Blank/whitespace
    }

    with pytest.raises(IngestionError) as exc_info:
        ingest_challenge_item(payload, db_session)

    assert "provenance" in str(exc_info.value).lower()
    assert db_session.query(Challenge).count() == 0


def test_ingestion_success_and_auto_calculation(db_session, valid_challenge_payload):
    """Valid challenge must ingest successfully with auto-computed CTRs, winning variant, z-score."""
    challenge = ingest_challenge_item(valid_challenge_payload, db_session)

    assert challenge.id == valid_challenge_payload["id"]
    assert challenge.title == valid_challenge_payload["title"]
    assert challenge.ctr_a == pytest.approx(4200 / 50000, rel=1e-4)
    assert challenge.ctr_b == pytest.approx(3500 / 50000, rel=1e-4)
    assert challenge.winning_variant == "A"
    assert challenge.z_score > 0
    assert challenge.p_value < 0.05
    assert challenge.is_active is True

    # Verify database persistence
    persisted = db_session.query(Challenge).filter_by(id=challenge.id).first()
    assert persisted is not None
    assert persisted.title == valid_challenge_payload["title"]
    assert persisted.winning_variant == "A"


def test_public_challenge_schema_never_leaks_ground_truth(
    valid_challenge_payload, db_session
):
    """ChallengePublic schema must not expose CTRs, impressions, clicks, winning variant, or z/p stats."""
    challenge = ingest_challenge_item(valid_challenge_payload, db_session)
    public_dto = ChallengePublic.model_validate(challenge)

    public_dict = public_dto.model_dump()
    forbidden_keys = {
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
    }
    for key in forbidden_keys:
        assert key not in public_dict, (
            f"Ground truth field '{key}' leaked in ChallengePublic!"
        )

    allowed_keys = {"id", "title", "category", "thumbnail_a_url", "thumbnail_b_url"}
    assert set(public_dict.keys()) == allowed_keys


def test_challenge_receipt_reveals_ground_truth_and_predictions(
    db_session, valid_challenge_payload
):
    """ChallengeReceipt must include ground truth stats and attached model predictions."""
    challenge = ingest_challenge_item(valid_challenge_payload, db_session)

    # Attach a model prediction
    prediction = ModelPrediction(
        challenge_id=challenge.id,
        model_name="mock-vision-v1",
        model_version="1.0.0",
        predicted_variant="A",
        confidence=0.88,
        reasoning="High emotional arousal face creates higher click-through intent.",
        prompt_version="v1.0.0",
        token_count=120,
        latency_ms=45,
        cost_usd=0.0,
    )
    db_session.add(prediction)
    db_session.commit()
    db_session.refresh(challenge)

    receipt = ChallengeReceipt.model_validate(challenge)
    receipt_dict = receipt.model_dump()

    assert receipt_dict["winning_variant"] == "A"
    assert receipt_dict["impressions_a"] == 50000
    assert receipt_dict["clicks_a"] == 4200
    assert len(receipt_dict["predictions"]) == 1
    assert receipt_dict["predictions"][0]["model_name"] == "mock-vision-v1"
    assert receipt_dict["predictions"][0]["predicted_variant"] == "A"


def test_batch_ingestion_summary(db_session):
    """Batch ingestion must return clear summary of ingested vs. rejected items."""
    items = [
        {
            "title": "Valid Variant A Winner",
            "category": "youtube_thumbnails",
            "thumbnail_a_url": "/static/thumbnails/01_a.svg",
            "thumbnail_b_url": "/static/thumbnails/01_b.svg",
            "impressions_a": 40000,
            "clicks_a": 3600,  # 9%
            "impressions_b": 40000,
            "clicks_b": 2800,  # 7%
            "provenance_source": "Channel Alpha (DEMO DATA)",
        },
        {
            "title": "Rejected Underpowered",
            "category": "youtube_thumbnails",
            "thumbnail_a_url": "/static/thumbnails/02_a.svg",
            "thumbnail_b_url": "/static/thumbnails/02_b.svg",
            "impressions_a": 10000,
            "clicks_a": 1000,
            "impressions_b": 10000,
            "clicks_b": 700,
            "provenance_source": "Channel Beta (DEMO DATA)",
        },
    ]

    summary = ingest_batch(items, db_session)
    assert summary.total_submitted == 2
    assert summary.ingested_count == 1
    assert summary.rejected_count == 1
    assert len(summary.rejections) == 1
    assert summary.rejections[0]["title"] == "Rejected Underpowered"
    assert "Insufficient impressions" in summary.rejections[0]["reason"]


@pytest.mark.asyncio
async def test_admin_api_ingest_endpoint(db_session):
    """Admin endpoint /api/admin/ingest must process JSON batch and return summary."""
    app.dependency_overrides[get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "challenges": [
                {
                    "title": "API Ingested Challenge",
                    "category": "youtube_thumbnails",
                    "thumbnail_a_url": "/static/thumbnails/api_a.svg",
                    "thumbnail_b_url": "/static/thumbnails/api_b.svg",
                    "impressions_a": 35000,
                    "clicks_a": 3150,
                    "impressions_b": 35000,
                    "clicks_b": 2450,
                    "provenance_source": "API Seed (DEMO DATA)",
                }
            ]
        }
        response = await client.post("/api/admin/ingest", json=payload)

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["total_submitted"] == 1
    assert data["ingested_count"] == 1
    assert data["rejected_count"] == 0


def test_seed_challenges_file_integrity():
    """Verify that backend/data/seed_challenges.json exists and has 36 valid items."""
    seed_file = Path("backend/data/seed_challenges.json")
    assert seed_file.exists(), "backend/data/seed_challenges.json does not exist!"

    with open(seed_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    challenges = data if isinstance(data, list) else data.get("challenges", [])
    assert len(challenges) == 36, f"Expected 36 seed challenges, got {len(challenges)}"

    from app.core.stats import validate_significance_gate

    for idx, item in enumerate(challenges, 1):
        assert "title" in item
        assert "provenance_source" in item
        assert "DEMO DATA" in item["provenance_source"], (
            f"Item {idx} missing DEMO DATA label"
        )
        assert item["impressions_a"] >= 20000
        assert item["impressions_b"] >= 20000

        gate = validate_significance_gate(
            impressions_a=item["impressions_a"],
            clicks_a=item["clicks_a"],
            impressions_b=item["impressions_b"],
            clicks_b=item["clicks_b"],
        )
        assert gate.is_valid, (
            f"Seed item {idx} ('{item['title']}') failed gate: {gate.rejection_reason}"
        )


@pytest.mark.asyncio
async def test_static_thumbnail_serving():
    """Verify that FastAPI serves static thumbnail SVGs via /static/thumbnails/."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/static/thumbnails/challenge_01_a.svg")
        assert response.status_code == 200
        assert "image/svg+xml" in response.headers.get("content-type", "")
        assert "<svg" in response.text
