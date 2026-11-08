"""Contract and specification tests for evaluation harness and mock baseline runner.

Verifies:
1. Pinned prompt version v1.0.0 and prompt template generation.
2. 100% determinism of mock vision models across repeated runs.
3. Characteristics and accuracy distributions for all 3 mock baseline models:
   - mock-frontier-v1 (~72% target accuracy, ~850 tokens, ~1100ms, $0.003/eval)
   - mock-compact-v1 (~61% target accuracy, ~420 tokens, ~350ms, $0.0006/eval)
   - mock-heuristic-v1 (~53% target accuracy, ~150 tokens, ~80ms, $0.0001/eval)
4. Database persistence and idempotency of ModelPrediction records.
5. Association with Challenge.predictions relationship.
6. OpenRouter adapter graceful fallback when API key is missing.
7. OpenRouter response parsing and cost/token metric extraction.
8. Batch baseline runner execution across challenges.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from app.db.base import Base
from app.eval.mock_models import (
    MOCK_MODELS,
    evaluate_mock_model,
    get_mock_model_specs,
)
from app.eval.openrouter_adapter import (
    OpenRouterAdapter,
    OpenRouterConfigError,
)
from app.eval.prompts import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    format_user_prompt,
    get_system_prompt,
)
from app.eval.runner import (
    DEFAULT_BASELINE_MODELS,
    run_baseline_models_for_challenge,
    run_baselines_for_all_challenges,
)
from app.models.challenge import Challenge, ModelPrediction
from app.models.eval_run import EvalRun
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
def sample_challenge(db_session):
    """Create and persist a sample challenge item for testing."""
    challenge = Challenge(
        id="c-test-101",
        title="I Built 100 Houses In 24 Hours",
        category="entertainment",
        thumbnail_a_url="/static/thumbnails/challenge_01_a.svg",
        thumbnail_b_url="/static/thumbnails/challenge_01_b.svg",
        impressions_a=50000,
        clicks_a=4200,
        ctr_a=0.084,
        impressions_b=50000,
        clicks_b=3100,
        ctr_b=0.062,
        winning_variant="A",
        z_score=13.25,
        p_value=0.00001,
        provenance_source="youtube_ab_archive_v1",
        is_active=True,
    )
    db_session.add(challenge)
    db_session.commit()
    db_session.refresh(challenge)
    return challenge


@pytest.fixture
def batch_challenges(db_session):
    """Create and persist a batch of 36 challenges for distribution verification."""
    challenges = []
    for i in range(1, 37):
        winning = "A" if (i % 2 == 1) else "B"
        ctr_a = 0.080 if winning == "A" else 0.055
        ctr_b = 0.055 if winning == "A" else 0.080
        c = Challenge(
            id=f"c-batch-{i:03d}",
            title=f"Sample Benchmark Video #{i:02d}",
            category="education" if i % 2 == 0 else "tech",
            thumbnail_a_url=f"/static/thumbnails/challenge_{i:02d}_a.svg",
            thumbnail_b_url=f"/static/thumbnails/challenge_{i:02d}_b.svg",
            impressions_a=40000,
            clicks_a=int(40000 * ctr_a),
            ctr_a=ctr_a,
            impressions_b=40000,
            clicks_b=int(40000 * ctr_b),
            ctr_b=ctr_b,
            winning_variant=winning,
            z_score=10.5,
            p_value=0.0001,
            provenance_source="youtube_ab_archive_v1",
            is_active=True,
        )
        db_session.add(c)
        challenges.append(c)
    db_session.commit()
    for c in challenges:
        db_session.refresh(c)
    return challenges


class TestPromptVersioning:
    """Test suite for versioned evaluation prompts."""

    def test_prompt_version_pinned(self):
        """Prompt version must be strictly pinned to v1.0.0."""
        assert PROMPT_VERSION == "v1.0.0"

    def test_system_prompt_content(self):
        """System prompt must establish expert YouTube audience analyst role."""
        prompt = get_system_prompt()
        assert prompt == SYSTEM_PROMPT
        assert "expert YouTube audience analyst" in prompt
        assert "click-through-rate" in prompt or "CTR" in prompt
        assert "predicted_variant" in prompt
        assert "confidence" in prompt

    def test_format_user_prompt(self, sample_challenge):
        """User prompt must contain title, category, and evaluation instructions."""
        prompt = format_user_prompt(
            title=sample_challenge.title,
            category=sample_challenge.category,
            thumbnail_a_url=sample_challenge.thumbnail_a_url,
            thumbnail_b_url=sample_challenge.thumbnail_b_url,
        )
        assert sample_challenge.title in prompt
        assert sample_challenge.category in prompt
        assert "Variant A" in prompt
        assert "Variant B" in prompt


class TestDeterministicMockModels:
    """Test suite for deterministic mock vision models."""

    def test_determinism_across_repeated_runs(self, sample_challenge):
        """Running the same mock model 10 times on the same challenge yields identical results."""
        model_name = "mock-frontier-v1"
        first_eval = evaluate_mock_model(sample_challenge, model_name)

        for _ in range(9):
            repeat_eval = evaluate_mock_model(sample_challenge, model_name)
            assert repeat_eval.predicted_variant == first_eval.predicted_variant
            assert repeat_eval.confidence == first_eval.confidence
            assert repeat_eval.token_count == first_eval.token_count
            assert repeat_eval.latency_ms == first_eval.latency_ms
            assert repeat_eval.cost_usd == first_eval.cost_usd
            assert repeat_eval.reasoning == first_eval.reasoning
            assert repeat_eval.prompt_version == first_eval.prompt_version

    def test_all_three_mock_models_available(self):
        """All 3 required baseline models must be registered in specs."""
        specs = get_mock_model_specs()
        assert "mock-frontier-v1" in specs
        assert "mock-compact-v1" in specs
        assert "mock-heuristic-v1" in specs
        assert len(specs) == 3

    @pytest.mark.parametrize(
        "model_name,expected_tokens_min,expected_tokens_max,expected_latency_min,expected_latency_max,expected_cost",
        [
            ("mock-frontier-v1", 750, 950, 900, 1300, 0.003),
            ("mock-compact-v1", 350, 490, 250, 450, 0.0006),
            ("mock-heuristic-v1", 100, 200, 40, 120, 0.0001),
        ],
    )
    def test_mock_model_specs_and_ranges(
        self,
        sample_challenge,
        model_name,
        expected_tokens_min,
        expected_tokens_max,
        expected_latency_min,
        expected_latency_max,
        expected_cost,
    ):
        """Mock models must emit realistic token, latency, and cost telemetry within spec ranges."""
        res = evaluate_mock_model(sample_challenge, model_name)
        assert res.predicted_variant in ("A", "B")
        assert 0.50 <= res.confidence <= 1.00
        assert expected_tokens_min <= res.token_count <= expected_tokens_max
        assert expected_latency_min <= res.latency_ms <= expected_latency_max
        assert pytest.approx(res.cost_usd, rel=1e-3) == expected_cost
        assert len(res.reasoning.strip()) > 30

    def test_mock_accuracy_distributions_across_benchmark(self, batch_challenges):
        """Over the 36-item benchmark, models reflect expected accuracy tiers:
        frontier (~72%), compact (~61%), heuristic (~53%).
        """
        frontier_correct = 0
        compact_correct = 0
        heuristic_correct = 0

        for c in batch_challenges:
            if evaluate_mock_model(c, "mock-frontier-v1").predicted_variant == c.winning_variant:
                frontier_correct += 1
            if evaluate_mock_model(c, "mock-compact-v1").predicted_variant == c.winning_variant:
                compact_correct += 1
            if evaluate_mock_model(c, "mock-heuristic-v1").predicted_variant == c.winning_variant:
                heuristic_correct += 1

        frontier_acc = frontier_correct / len(batch_challenges)
        compact_acc = compact_correct / len(batch_challenges)
        heuristic_acc = heuristic_correct / len(batch_challenges)

        # Frontier ~72% (bound between 63% and 82%)
        assert 0.63 <= frontier_acc <= 0.82
        # Compact ~61% (bound between 52% and 72%)
        assert 0.52 <= compact_acc <= 0.72
        # Heuristic ~53% (bound between 44% and 62%)
        assert 0.44 <= heuristic_acc <= 0.62
        # Relative ordering must hold: Frontier >= Compact >= Heuristic
        assert frontier_acc >= compact_acc >= heuristic_acc

    def test_mock_reasoning_diversity(self, batch_challenges):
        """Mock models should generate varied, non-trivial analytical reasoning text."""
        reasonings = set()
        for c in batch_challenges[:10]:
            res = evaluate_mock_model(c, "mock-frontier-v1")
            reasonings.add(res.reasoning)
        # Should have multiple distinct reasoning explanations across 10 items
        assert len(reasonings) >= 4


class TestRunnerServiceAndPersistence:
    """Test suite for evaluation runner service and database persistence."""

    def test_run_baseline_models_persists_to_db(self, db_session, sample_challenge):
        """Running baseline models creates and links ModelPrediction rows in the DB."""
        preds = run_baseline_models_for_challenge(sample_challenge, db_session)
        assert len(preds) == 3

        # Verify saved in DB
        db_preds = (
            db_session.query(ModelPrediction)
            .filter_by(challenge_id=sample_challenge.id)
            .all()
        )
        assert len(db_preds) == 3

        model_names = {p.model_name for p in db_preds}
        assert model_names == {
            "mock-frontier-v1",
            "mock-compact-v1",
            "mock-heuristic-v1",
        }

        # Verify relationship on Challenge
        db_session.refresh(sample_challenge)
        assert len(sample_challenge.predictions) == 3
        for pred in sample_challenge.predictions:
            assert pred.prompt_version == "v1.0.0"
            assert pred.predicted_variant in ("A", "B")
            assert pred.token_count > 0
            assert pred.latency_ms > 0

    def test_run_baseline_models_is_idempotent(self, db_session, sample_challenge):
        """Calling runner repeatedly on the same challenge reuses existing predictions."""
        preds1 = run_baseline_models_for_challenge(sample_challenge, db_session)
        preds2 = run_baseline_models_for_challenge(sample_challenge, db_session)

        assert len(preds1) == 3
        assert len(preds2) == 3
        assert [p.id for p in preds1] == [p.id for p in preds2]

        total_in_db = (
            db_session.query(ModelPrediction)
            .filter_by(challenge_id=sample_challenge.id)
            .count()
        )
        assert total_in_db == 3

    def test_run_baselines_for_all_challenges(self, db_session, batch_challenges):
        """Batch runner computes predictions for all active challenges in the DB."""
        summary = run_baselines_for_all_challenges(db_session)

        assert summary["total_challenges"] == 36
        assert summary["predictions_created"] == 36 * 3
        assert summary["predictions_reused"] == 0

        # Check an EvalRun record was created for tracking
        eval_runs = db_session.query(EvalRun).all()
        assert len(eval_runs) >= 3

        # Run again, verify all predictions are reused
        summary2 = run_baselines_for_all_challenges(db_session)
        assert summary2["predictions_created"] == 0
        assert summary2["predictions_reused"] == 36 * 3


class TestOpenRouterAdapter:
    """Test suite for OpenRouter live multimodal provider adapter."""

    def test_graceful_handling_when_api_key_missing(self, monkeypatch):
        """Adapter signals unavailability when OPENROUTER_API_KEY is not set."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        adapter = OpenRouterAdapter()
        assert adapter.is_available() is False

        with pytest.raises(OpenRouterConfigError, match="OPENROUTER_API_KEY"):
            adapter.evaluate(
                challenge_id="c-test",
                title="Title",
                category="vlog",
                thumbnail_a_url="/thumb_a.svg",
                thumbnail_b_url="/thumb_b.svg",
            )

    def test_openrouter_evaluation_with_mocked_http_response(self, monkeypatch):
        """Adapter correctly formats request and parses OpenRouter vision API response."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-mock-test-key-12345")
        adapter = OpenRouterAdapter(model_name="google/gemini-2.0-flash-001")
        assert adapter.is_available() is True

        mock_payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "predicted_variant": "A",
                                "confidence": 0.88,
                                "reasoning": "Thumbnail A uses high focal contrast and emotive facial framing.",
                            }
                        )
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 420,
                "completion_tokens": 65,
                "total_tokens": 485,
            },
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_payload
        mock_response.headers = {
            "x-openrouter-cost": "0.00072",
        }

        with patch("httpx.Client.post", return_value=mock_response) as mock_post:
            result = adapter.evaluate(
                challenge_id="c-test",
                title="Building a Jetpack",
                category="science",
                thumbnail_a_url="https://humark.local/thumb_a.svg",
                thumbnail_b_url="https://humark.local/thumb_b.svg",
            )

            assert mock_post.called
            call_kwargs = mock_post.call_args[1]
            assert "messages" in call_kwargs["json"]
            assert call_kwargs["headers"]["Authorization"] == "Bearer sk-or-v1-mock-test-key-12345"

            assert result.predicted_variant == "A"
            assert result.confidence == 0.88
            assert "emotive facial framing" in result.reasoning
            assert result.token_count == 485
            assert result.cost_usd == 0.00072
            assert result.prompt_version == PROMPT_VERSION
