"""Percentile Calculation Engine benchmarking human performance against WONO empirical study.

WONO Empirical Benchmark:
- 7,030 human participants
- Human Benchmark Mean (mu): 0.528 (52.8%)
- Human Benchmark Std (sigma): 0.094 (9.4%)
- Frontier AI Baseline: 0.750 (75.0% accuracy, sitting at ~98.9th percentile)
- Top 2% Threshold: 0.722 (z ~ 2.05)
"""

from __future__ import annotations

import math
from pydantic import BaseModel, ConfigDict, Field

HUMAN_BENCHMARK_MEAN: float = 0.528
HUMAN_BENCHMARK_STD: float = 0.094
FRONTIER_AI_ACCURACY: float = 0.750
TOP_2_PERCENT_THRESHOLD: float = 0.722

# Curve sampling bounds
CURVE_X_MIN: float = 0.20
CURVE_X_MAX: float = 0.85
CURVE_NUM_POINTS: int = 25


def _gaussian_pdf(x: float, mu: float = HUMAN_BENCHMARK_MEAN, sigma: float = HUMAN_BENCHMARK_STD) -> float:
    """Compute the Gaussian probability density function f(x)."""
    coef = 1.0 / (sigma * math.sqrt(2.0 * math.pi))
    exponent = -0.5 * ((x - mu) / sigma) ** 2
    return coef * math.exp(exponent)


def _normal_cdf(z: float) -> float:
    """Compute cumulative standard normal distribution Phi(z)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


class PercentileBenchmark(BaseModel):
    """Percentile benchmark metrics relative to 7,030 human participant baseline."""

    model_config = ConfigDict(from_attributes=True)

    accuracy: float = Field(description="Participant accuracy ratio")
    z_score: float = Field(description="Standardized z-score relative to human population")
    percentile: float = Field(description="Cumulative percentile rank clamped to [0.1, 99.9]")
    is_top_2_percent: bool = Field(description="True if participant percentile >= 98.0")
    beats_frontier_ai: bool = Field(description="True if participant accuracy > FRONTIER_AI_ACCURACY")
    tier_label: str = Field(description="Categorical standing label")
    curve_points: list[tuple[float, float]] = Field(
        description="25 normalized (x, y) coordinates along the Gaussian bell curve"
    )
    user_point: tuple[float, float] = Field(
        description="Normalized (x, y) coordinate for participant standing on curve"
    )
    frontier_point: tuple[float, float] = Field(
        description="Normalized (x, y) coordinate for frontier AI standing on curve"
    )


def calculate_human_percentile(accuracy: float, total_attempts: int = 0) -> PercentileBenchmark:
    """Compute human percentile ranking and bell curve coordinates against WONO distribution.

    Args:
        accuracy: Participant accuracy ratio (e.g. 0.70 for 70%).
        total_attempts: Number of challenge attempts in the session.

    Returns:
        PercentileBenchmark containing z-score, percentile, tier labels, and bell curve points.
    """
    z = (accuracy - HUMAN_BENCHMARK_MEAN) / HUMAN_BENCHMARK_STD
    raw_percentile = _normal_cdf(z) * 100.0
    percentile = round(max(0.1, min(99.9, raw_percentile)), 1)

    is_top_2_percent = percentile >= 98.0
    beats_frontier_ai = accuracy > FRONTIER_AI_ACCURACY

    if beats_frontier_ai:
        tier_label = "Top 2% Elite Evaluator (Outperforming Frontier AI)"
    elif is_top_2_percent:
        tier_label = "Top 2% Human Tier (Nearing Frontier AI)"
    elif percentile >= 70.0:
        tier_label = "High Performer (Above Average Human Intuition)"
    elif percentile >= 40.0:
        tier_label = "Median Human Baseline"
    else:
        tier_label = "Calibration Tier"

    # Peak PDF at mu for normalization
    peak_pdf = _gaussian_pdf(HUMAN_BENCHMARK_MEAN)

    # Generate 25 normalized curve sampling points
    step = (CURVE_X_MAX - CURVE_X_MIN) / (CURVE_NUM_POINTS - 1)
    curve_points: list[tuple[float, float]] = []
    for i in range(CURVE_NUM_POINTS):
        x = CURVE_X_MIN + i * step
        pdf_val = _gaussian_pdf(x)
        y_norm = round(pdf_val / peak_pdf, 4)
        curve_points.append((round(x, 4), y_norm))

    # User coordinate on curve
    clamped_user_x = max(CURVE_X_MIN, min(CURVE_X_MAX, accuracy))
    user_y = round(_gaussian_pdf(clamped_user_x) / peak_pdf, 4)
    user_point = (round(accuracy, 4), user_y)

    # Frontier AI coordinate on curve
    frontier_y = round(_gaussian_pdf(FRONTIER_AI_ACCURACY) / peak_pdf, 4)
    frontier_point = (round(FRONTIER_AI_ACCURACY, 4), frontier_y)

    return PercentileBenchmark(
        accuracy=round(accuracy, 4),
        z_score=round(z, 2),
        percentile=percentile,
        is_top_2_percent=is_top_2_percent,
        beats_frontier_ai=beats_frontier_ai,
        tier_label=tier_label,
        curve_points=curve_points,
        user_point=user_point,
        frontier_point=frontier_point,
    )
