"""Contract tests for statistical significance engine and Wilson score intervals.

These tests define the behavioral contract for ADR-002 (Statistical Significance Gate)
and ADR-005 (Scorecard Confidence Telemetry).
"""

import math

import pytest
from app.core.stats import (
    GateResult,
    WilsonInterval,
    ZTestResult,
    calculate_two_proportion_z_test,
    calculate_wilson_score_interval,
    validate_significance_gate,
)


class TestTwoProportionZTest:
    """Contract tests for calculate_two_proportion_z_test."""

    def test_statistically_significant_challenge(self):
        """High volume challenge with distinct CTRs must yield p < 0.001."""
        # Variant A: 50,000 imp, 2,500 clicks (5.0%)
        # Variant B: 50,000 imp, 2,000 clicks (4.0%)
        result = calculate_two_proportion_z_test(
            impressions_a=50000,
            clicks_a=2500,
            impressions_b=50000,
            clicks_b=2000,
        )

        assert isinstance(result, ZTestResult)
        assert math.isclose(result.ctr_a, 0.05, abs_tol=1e-6)
        assert math.isclose(result.ctr_b, 0.04, abs_tol=1e-6)
        assert math.isclose(result.pooled_proportion, 0.045, abs_tol=1e-6)
        assert math.isclose(result.standard_error, 0.0013111, rel_tol=1e-3)
        assert math.isclose(result.z_score, 7.627, rel_tol=1e-3)
        assert result.p_value < 0.001
        assert result.p_value >= 0.0

    def test_zero_clicks_edge_case(self):
        """Zero clicks on both variants must yield z=0.0 and p=1.0 without dividing by zero."""
        result = calculate_two_proportion_z_test(
            impressions_a=50000,
            clicks_a=0,
            impressions_b=50000,
            clicks_b=0,
        )

        assert result.ctr_a == 0.0
        assert result.ctr_b == 0.0
        assert result.pooled_proportion == 0.0
        assert result.standard_error == 0.0
        assert result.z_score == 0.0
        assert result.p_value == 1.0

    def test_identical_proportions(self):
        """Equal non-zero proportions must yield z=0.0 and p=1.0."""
        result = calculate_two_proportion_z_test(
            impressions_a=30000,
            clicks_a=1500,
            impressions_b=30000,
            clicks_b=1500,
        )

        assert math.isclose(result.ctr_a, 0.05, abs_tol=1e-6)
        assert math.isclose(result.ctr_b, 0.05, abs_tol=1e-6)
        assert result.z_score == 0.0
        assert result.p_value == 1.0

    def test_negative_or_zero_impressions_raise_value_error(self):
        """Non-positive impressions must raise ValueError."""
        with pytest.raises(ValueError, match="impressions must be positive"):
            calculate_two_proportion_z_test(0, 0, 50000, 1000)

        with pytest.raises(ValueError, match="impressions must be positive"):
            calculate_two_proportion_z_test(50000, 1000, -10, 0)

    def test_clicks_exceeding_impressions_raise_value_error(self):
        """Clicks exceeding impressions (CTR > 1.0) must raise ValueError."""
        with pytest.raises(ValueError, match="clicks cannot exceed impressions"):
            calculate_two_proportion_z_test(100, 101, 100, 50)

        with pytest.raises(ValueError, match="clicks cannot exceed impressions"):
            calculate_two_proportion_z_test(100, 50, 100, 150)

    def test_negative_clicks_raise_value_error(self):
        """Negative clicks must raise ValueError."""
        with pytest.raises(ValueError, match="clicks cannot be negative"):
            calculate_two_proportion_z_test(100, -1, 100, 5)


class TestSignificanceGate:
    """Contract tests for validate_significance_gate (ADR-002 Hard Gate)."""

    def test_valid_statistically_significant_challenge(self):
        """Items meeting impressions >= 20k and p < 0.05 pass the gate."""
        # A: 50,000 imp, 2,500 clicks (5.0%) vs B: 50,000 imp, 2,000 clicks (4.0%)
        gate = validate_significance_gate(
            impressions_a=50000,
            clicks_a=2500,
            impressions_b=50000,
            clicks_b=2000,
            min_impressions=20000,
            alpha=0.05,
        )

        assert isinstance(gate, GateResult)
        assert gate.is_valid is True
        assert gate.rejection_reason is None
        assert gate.z_test_result.p_value < 0.001

    def test_failure_due_to_sample_size(self):
        """Items with impressions < min_impressions fail even if p < 0.01."""
        # A: 15,000 imp, 1,000 clicks (6.67%) vs B: 18,000 imp, 800 clicks (4.44%)
        gate = validate_significance_gate(
            impressions_a=15000,
            clicks_a=1000,
            impressions_b=18000,
            clicks_b=800,
            min_impressions=20000,
            alpha=0.05,
        )

        assert gate.is_valid is False
        assert gate.rejection_reason is not None
        assert "insufficient impressions" in gate.rejection_reason.lower()
        # Z-test result is still computed for provenance telemetry
        assert gate.z_test_result.p_value < 0.01

    def test_failure_due_to_one_variant_below_threshold(self):
        """Variant A meets threshold, but Variant B fails threshold -> REJECT."""
        gate = validate_significance_gate(
            impressions_a=25000,
            clicks_a=1500,
            impressions_b=19999,
            clicks_b=1000,
            min_impressions=20000,
            alpha=0.05,
        )

        assert gate.is_valid is False
        assert gate.rejection_reason is not None
        assert (
            "19999" in gate.rejection_reason
            or "variant b" in gate.rejection_reason.lower()
        )

    def test_failure_due_to_p_value(self):
        """Items with sufficient impressions but p >= alpha fail the gate."""
        # A: 25,000 imp, 1,000 clicks (4.00%) vs B: 25,000 imp, 1,010 clicks (4.04%) -> p ~ 0.82
        gate = validate_significance_gate(
            impressions_a=25000,
            clicks_a=1000,
            impressions_b=25000,
            clicks_b=1010,
            min_impressions=20000,
            alpha=0.05,
        )

        assert gate.is_valid is False
        assert gate.rejection_reason is not None
        assert (
            "p-value" in gate.rejection_reason.lower()
            or "insignificant" in gate.rejection_reason.lower()
        )
        assert gate.z_test_result.p_value >= 0.05

    def test_custom_min_impressions_and_alpha(self):
        """Custom threshold overrides must be strictly honored."""
        # A: 10,000 imp, 600 clicks vs B: 10,000 imp, 450 clicks
        # p ~ 0.0001, passes when min_impressions=10000, alpha=0.01
        gate = validate_significance_gate(
            impressions_a=10000,
            clicks_a=600,
            impressions_b=10000,
            clicks_b=450,
            min_impressions=10000,
            alpha=0.01,
        )
        assert gate.is_valid is True
        assert gate.rejection_reason is None


class TestWilsonScoreInterval:
    """Contract tests for calculate_wilson_score_interval (ADR-005)."""

    def test_wilson_score_perfect_success_10_of_10(self):
        """10/10 successes at 95% confidence."""
        interval = calculate_wilson_score_interval(
            successes=10, total=10, confidence=0.95
        )

        assert isinstance(interval, WilsonInterval)
        # Wilson interval for 10/10: lower ~0.7225, upper == 1.0, center ~0.8612
        assert math.isclose(interval.lower, 0.722467, abs_tol=1e-4)
        assert math.isclose(interval.upper, 1.0, abs_tol=1e-4)
        assert math.isclose(interval.center, 0.861234, abs_tol=1e-4)
        assert interval.sample_size_warning is True  # 10 < 30

    def test_wilson_score_zero_success_0_of_10(self):
        """0/10 successes at 95% confidence."""
        interval = calculate_wilson_score_interval(
            successes=0, total=10, confidence=0.95
        )

        # Wilson interval for 0/10: lower == 0.0, upper ~0.2775, center ~0.1388
        assert math.isclose(interval.lower, 0.0, abs_tol=1e-4)
        assert math.isclose(interval.upper, 0.277533, abs_tol=1e-4)
        assert math.isclose(interval.center, 0.138766, abs_tol=1e-4)
        assert interval.sample_size_warning is True

    def test_wilson_score_intermediate_7_of_10(self):
        """7/10 successes at 95% confidence (Game Round 1 scenario)."""
        interval = calculate_wilson_score_interval(
            successes=7, total=10, confidence=0.95
        )

        # Wilson interval for 7/10: lower ~0.3968, upper ~0.8922, center ~0.6445
        assert math.isclose(interval.lower, 0.396778, abs_tol=1e-4)
        assert math.isclose(interval.upper, 0.892209, abs_tol=1e-4)
        assert math.isclose(interval.center, 0.644493, abs_tol=1e-4)
        assert interval.sample_size_warning is True

    def test_wilson_score_edge_case_0_of_0(self):
        """0/0 (no attempts yet) must return full span [0.0, 1.0] with center 0.5."""
        interval = calculate_wilson_score_interval(
            successes=0, total=0, confidence=0.95
        )

        assert interval.lower == 0.0
        assert interval.upper == 1.0
        assert interval.center == 0.5
        assert interval.sample_size_warning is True

    def test_sample_size_warning_threshold_at_30(self):
        """sample_size_warning must be True when total < 30, False when total >= 30."""
        interval_29 = calculate_wilson_score_interval(successes=20, total=29)
        assert interval_29.sample_size_warning is True

        interval_30 = calculate_wilson_score_interval(successes=21, total=30)
        assert interval_30.sample_size_warning is False

        interval_50 = calculate_wilson_score_interval(successes=35, total=50)
        assert interval_50.sample_size_warning is False

    def test_wilson_score_invalid_inputs(self):
        """Invalid bounds or parameters must raise ValueError."""
        with pytest.raises(ValueError, match="successes cannot be negative"):
            calculate_wilson_score_interval(successes=-1, total=10)

        with pytest.raises(ValueError, match="total cannot be negative"):
            calculate_wilson_score_interval(successes=0, total=-5)

        with pytest.raises(ValueError, match="successes cannot exceed total"):
            calculate_wilson_score_interval(successes=11, total=10)

        with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
            calculate_wilson_score_interval(successes=5, total=10, confidence=1.5)

        with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
            calculate_wilson_score_interval(successes=5, total=10, confidence=0.0)
