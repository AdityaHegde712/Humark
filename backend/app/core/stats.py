"""Statistical engine for hypothesis testing and confidence estimation.

This module provides implementations for:
1. Two-proportion z-tests for A/B thumbnail comparisons.
2. Hard significance gate enforcement (ADR-002: N >= 20,000, p < 0.05).
3. Wilson score confidence intervals for game scorecards (ADR-005).
"""

from __future__ import annotations

import math

import scipy.stats
from pydantic import BaseModel, ConfigDict, Field


class ZTestResult(BaseModel):
    """Result of a two-proportion hypothesis test."""

    model_config = ConfigDict(frozen=True)

    ctr_a: float = Field(..., description="Click-through rate of variant A.")
    ctr_b: float = Field(..., description="Click-through rate of variant B.")
    pooled_proportion: float = Field(
        ..., description="Combined CTR across both variants."
    )
    standard_error: float = Field(
        ..., description="Standard error under null hypothesis."
    )
    z_score: float = Field(..., description="Standardized test statistic.")
    p_value: float = Field(..., description="Two-tailed p-value.")


class GateResult(BaseModel):
    """Validation result for challenge significance gate."""

    model_config = ConfigDict(frozen=True)

    is_valid: bool = Field(
        ..., description="True if challenge passes all gate criteria."
    )
    rejection_reason: str | None = Field(
        default=None,
        description="Reason for rejection, or None if valid.",
    )
    z_test_result: ZTestResult = Field(
        ..., description="Full statistical test results."
    )


class WilsonInterval(BaseModel):
    """Wilson score confidence interval for binomial proportions."""

    model_config = ConfigDict(frozen=True)

    lower: float = Field(..., description="Lower confidence bound [0.0, 1.0].")
    upper: float = Field(..., description="Upper confidence bound [0.0, 1.0].")
    center: float = Field(..., description="Adjusted center midpoint.")
    sample_size_warning: bool = Field(
        ...,
        description="True when total sample size is under 30 observations.",
    )


def calculate_two_proportion_z_test(
    impressions_a: int,
    clicks_a: int,
    impressions_b: int,
    clicks_b: int,
) -> ZTestResult:
    """Calculate a two-proportion z-test comparing click-through rates.

    Args:
        impressions_a: Total impressions for variant A (> 0).
        clicks_a: Total clicks for variant A (>= 0 and <= impressions_a).
        impressions_b: Total impressions for variant B (> 0).
        clicks_b: Total clicks for variant B (>= 0 and <= impressions_b).

    Returns:
        ZTestResult with computed rates, standard error, z-score, and two-tailed p-value.

    Raises:
        ValueError: If impressions are not positive, clicks are negative,
            or clicks exceed impressions.
    """
    if impressions_a <= 0 or impressions_b <= 0:
        raise ValueError("impressions must be positive integers")
    if clicks_a < 0 or clicks_b < 0:
        raise ValueError("clicks cannot be negative")
    if clicks_a > impressions_a or clicks_b > impressions_b:
        raise ValueError("clicks cannot exceed impressions")

    ctr_a = clicks_a / impressions_a
    ctr_b = clicks_b / impressions_b

    total_clicks = clicks_a + clicks_b
    total_impressions = impressions_a + impressions_b
    pooled_p = total_clicks / total_impressions

    if pooled_p == 0.0 or pooled_p == 1.0 or ctr_a == ctr_b:
        return ZTestResult(
            ctr_a=float(ctr_a),
            ctr_b=float(ctr_b),
            pooled_proportion=float(pooled_p),
            standard_error=0.0,
            z_score=0.0,
            p_value=1.0,
        )

    variance_term = (
        pooled_p * (1.0 - pooled_p) * (1.0 / impressions_a + 1.0 / impressions_b)
    )
    standard_error = math.sqrt(variance_term)

    if standard_error == 0.0:
        return ZTestResult(
            ctr_a=float(ctr_a),
            ctr_b=float(ctr_b),
            pooled_proportion=float(pooled_p),
            standard_error=0.0,
            z_score=0.0,
            p_value=1.0,
        )

    z_score = (ctr_a - ctr_b) / standard_error
    p_value = float(2.0 * scipy.stats.norm.sf(abs(z_score)))

    return ZTestResult(
        ctr_a=float(ctr_a),
        ctr_b=float(ctr_b),
        pooled_proportion=float(pooled_p),
        standard_error=float(standard_error),
        z_score=float(z_score),
        p_value=float(p_value),
    )


def validate_significance_gate(
    impressions_a: int,
    clicks_a: int,
    impressions_b: int,
    clicks_b: int,
    min_impressions: int = 20000,
    alpha: float = 0.05,
) -> GateResult:
    """Enforce ADR-002 statistical significance hard gate.

    A challenge passes if and only if:
    1. impressions_a >= min_impressions
    2. impressions_b >= min_impressions
    3. p_value < alpha

    Args:
        impressions_a: Total impressions for variant A.
        clicks_a: Total clicks for variant A.
        impressions_b: Total impressions for variant B.
        clicks_b: Total clicks for variant B.
        min_impressions: Minimum impressions required per variant (default: 20,000).
        alpha: Maximum acceptable two-tailed p-value (default: 0.05).

    Returns:
        GateResult indicating validity, rejection reason (if rejected), and test metrics.
    """
    z_result = calculate_two_proportion_z_test(
        impressions_a=impressions_a,
        clicks_a=clicks_a,
        impressions_b=impressions_b,
        clicks_b=clicks_b,
    )

    rejection_reasons: list[str] = []

    if impressions_a < min_impressions or impressions_b < min_impressions:
        rejection_reasons.append(
            f"Insufficient impressions: variant A has {impressions_a}, "
            f"variant B has {impressions_b} (minimum required is {min_impressions})"
        )

    if z_result.p_value >= alpha:
        rejection_reasons.append(
            f"Statistically insignificant difference: p-value {z_result.p_value:.6f} >= alpha {alpha}"
        )

    if rejection_reasons:
        return GateResult(
            is_valid=False,
            rejection_reason="; ".join(rejection_reasons),
            z_test_result=z_result,
        )

    return GateResult(
        is_valid=True,
        rejection_reason=None,
        z_test_result=z_result,
    )


def calculate_wilson_score_interval(
    successes: int,
    total: int,
    confidence: float = 0.95,
) -> WilsonInterval:
    """Calculate exact Wilson score confidence interval for binomial accuracy.

    Follows the Agresti-Coull / Wilson score interval formulation.

    Args:
        successes: Number of correct predictions (>= 0).
        total: Number of total attempts (>= successes).
        confidence: Confidence level in range (0.0, 1.0) (default: 0.95).

    Returns:
        WilsonInterval with lower bound, upper bound, adjusted center,
        and sample size warning flag.

    Raises:
        ValueError: If parameters violate domain constraints.
    """
    if total < 0:
        raise ValueError("total cannot be negative")
    if successes < 0:
        raise ValueError("successes cannot be negative")
    if successes > total:
        raise ValueError("successes cannot exceed total")
    if confidence <= 0.0 or confidence >= 1.0:
        raise ValueError("confidence must be between 0 and 1")

    warning = total < 30

    if total == 0:
        return WilsonInterval(
            lower=0.0,
            upper=1.0,
            center=0.5,
            sample_size_warning=warning,
        )

    alpha = 1.0 - confidence
    z = float(scipy.stats.norm.ppf(1.0 - alpha / 2.0))
    p = successes / total

    z2 = z * z
    denominator = 1.0 + (z2 / total)
    center = (p + (z2 / (2.0 * total))) / denominator
    margin = (z / denominator) * math.sqrt(
        (p * (1.0 - p) / total) + (z2 / (4.0 * total * total))
    )

    lower = max(0.0, float(center - margin))
    upper = min(1.0, float(center + margin))

    return WilsonInterval(
        lower=lower,
        upper=upper,
        center=float(center),
        sample_size_warning=warning,
    )
