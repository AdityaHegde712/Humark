"""Deterministic mock vision models for offline baseline evaluation.

Implements ADR-003: Deterministic mock vision runner, zero API keys required,
pre-computing baseline answers with reproducible hashes, realistic tokens,
latency, and cost accounting.
"""

from dataclasses import dataclass
import hashlib
from typing import Any

from app.eval.prompts import PROMPT_VERSION


@dataclass(frozen=True)
class MockModelSpec:
    """Specification metadata for a mock baseline model."""

    name: str
    version: str
    target_accuracy: float
    base_tokens: int
    base_latency_ms: int
    cost_per_eval: float
    description: str


@dataclass(frozen=True)
class MockEvaluationResult:
    """Result of an evaluation run on a single challenge item."""

    model_name: str
    model_version: str
    predicted_variant: str  # "A" or "B"
    confidence: float
    reasoning: str
    prompt_version: str
    token_count: int
    latency_ms: int
    cost_usd: float


MOCK_MODELS: dict[str, MockModelSpec] = {
    "mock-frontier-v1": MockModelSpec(
        name="mock-frontier-v1",
        version="1.0.0",
        target_accuracy=0.72,
        base_tokens=850,
        base_latency_ms=1100,
        cost_per_eval=0.003,
        description="Simulates frontier multimodal model (GPT-4o / Claude 3.5 Sonnet class).",
    ),
    "mock-compact-v1": MockModelSpec(
        name="mock-compact-v1",
        version="1.0.0",
        target_accuracy=0.61,
        base_tokens=420,
        base_latency_ms=350,
        cost_per_eval=0.0006,
        description="Simulates fast lightweight vision model (Gemini Flash / Claude Haiku class).",
    ),
    "mock-heuristic-v1": MockModelSpec(
        name="mock-heuristic-v1",
        version="1.0.0",
        target_accuracy=0.53,
        base_tokens=150,
        base_latency_ms=80,
        cost_per_eval=0.0001,
        description="Simulates naive visual contrast and facial prominence heuristic.",
    ),
}


def get_mock_model_specs() -> dict[str, MockModelSpec]:
    """Return dictionary of available mock baseline model specifications."""
    return MOCK_MODELS


# Reasoning template banks per model tier and predicted variant
_FRONTIER_REASONING_TEMPLATES = [
    (
        "Variant {chosen} establishes superior visual hierarchy. The primary subject's emotive eye contact "
        "and clean separation from the background creates immediate cognitive fluency, maximizing CTR against '{title}'."
    ),
    (
        "Variant {chosen} excels in composition and focal tension. High dynamic contrast around the central action "
        "complements the curiosity gap of the title, creating stronger viewer intrigue than Variant {other}."
    ),
    (
        "Variant {chosen} demonstrates optimized mobile viewport legibility. Bold typographic weight paired with "
        "uncluttered negative space drives higher gaze retention and immediate value delivery in feed recommendations."
    ),
    (
        "Variant {chosen} leverages powerful narrative framing. The juxtaposition between subject expression "
        "and focal element triggers an urgent open loop that naturally outperforms Variant {other} in viewer conversion."
    ),
    (
        "Variant {chosen} balances vibrant warm foreground tones against controlled ambient shadows. "
        "This color grading directs viewer eye-path straight to the critical story element without visual noise."
    ),
]

_COMPACT_REASONING_TEMPLATES = [
    (
        "Variant {chosen} features larger, high-contrast typography and clearer subject silhouette, "
        "making it substantially more readable at smaller card sizes in mobile feeds."
    ),
    (
        "Variant {chosen} has a sharper focal point and brighter color saturation, which stands out "
        "more effectively against standard dark and light platform feed backgrounds."
    ),
    (
        "Variant {chosen} minimizes visual clutter and centers the emotional expression, providing "
        "quicker comprehension within the critical 300ms viewer scroll window."
    ),
    (
        "Variant {chosen} displays stronger visual contrast between the foreground subject and background, "
        "leading to higher click propensity over Variant {other}."
    ),
]

_HEURISTIC_REASONING_TEMPLATES = [
    (
        "Heuristic analysis detected higher peak luminance contrast and larger dominant subject bounding box in Variant {chosen}."
    ),
    (
        "Rule-based visual scan prioritized Variant {chosen} due to higher facial prominence index and saturated color distribution."
    ),
    (
        "Contrast and edge-detection heuristic favors Variant {chosen} for reduced background complexity and higher center-weighted energy."
    ),
]


def evaluate_mock_model(challenge: Any, model_name: str) -> MockEvaluationResult:
    """Deterministically evaluate a challenge item using a mock baseline vision model.

    Produces 100% reproducible predictions, tokens, latency, and reasoning based on
    SHA-256 hashes of challenge_id, model_name, and prompt_version.

    Args:
        challenge: Challenge model instance or object with id, winning_variant, title, category.
        model_name: Identifier of mock model ("mock-frontier-v1", "mock-compact-v1", "mock-heuristic-v1").

    Returns:
        MockEvaluationResult with deterministic predictions and metrics.

    Raises:
        ValueError: If model_name is not registered in MOCK_MODELS.
    """
    if model_name not in MOCK_MODELS:
        raise ValueError(
            f"Unknown mock model '{model_name}'. Available: {list(MOCK_MODELS.keys())}"
        )

    spec = MOCK_MODELS[model_name]
    challenge_id = str(getattr(challenge, "id", "unknown"))
    winning_variant = str(getattr(challenge, "winning_variant", "A"))
    title = str(getattr(challenge, "title", "Benchmark Challenge"))

    # 1. Deterministic challenge difficulty derived from challenge ID and prompt version
    diff_hash = hashlib.sha256(f"{challenge_id}:{PROMPT_VERSION}".encode("utf-8")).digest()
    challenge_difficulty = (int.from_bytes(diff_hash[:8], "big") % 1000) / 1000.0

    # Model accuracy gate: higher-capability models solve harder challenges
    is_correct = challenge_difficulty < spec.target_accuracy
    if is_correct:
        predicted_variant = winning_variant
    else:
        predicted_variant = "B" if winning_variant == "A" else "A"

    other_variant = "B" if predicted_variant == "A" else "A"

    # 2. Model-specific deterministic metrics derived from compound hash
    compound_key = f"{challenge_id}:{model_name}:{PROMPT_VERSION}"
    compound_hash = hashlib.sha256(compound_key.encode("utf-8")).digest()
    seed_int = int.from_bytes(compound_hash[:8], "big")
    seed_int_2 = int.from_bytes(compound_hash[8:16], "big")

    if model_name == "mock-frontier-v1":
        # Tokens: 850 +/- 40
        token_count = spec.base_tokens + (seed_int % 81) - 40
        # Latency: 1100 +/- 80 ms
        latency_ms = spec.base_latency_ms + (seed_int_2 % 161) - 80
        # Confidence: 0.72 - 0.92
        confidence = round(0.72 + ((seed_int >> 16) % 21) / 100.0, 2)
        template = _FRONTIER_REASONING_TEMPLATES[seed_int % len(_FRONTIER_REASONING_TEMPLATES)]
    elif model_name == "mock-compact-v1":
        # Tokens: 420 +/- 30
        token_count = spec.base_tokens + (seed_int % 61) - 30
        # Latency: 350 +/- 40 ms
        latency_ms = spec.base_latency_ms + (seed_int_2 % 81) - 40
        # Confidence: 0.62 - 0.80
        confidence = round(0.62 + ((seed_int >> 16) % 19) / 100.0, 2)
        template = _COMPACT_REASONING_TEMPLATES[seed_int % len(_COMPACT_REASONING_TEMPLATES)]
    else:  # mock-heuristic-v1
        # Tokens: 150 +/- 20
        token_count = spec.base_tokens + (seed_int % 41) - 20
        # Latency: 80 +/- 15 ms
        latency_ms = spec.base_latency_ms + (seed_int_2 % 31) - 15
        # Confidence: 0.53 - 0.63
        confidence = round(0.53 + ((seed_int >> 16) % 11) / 100.0, 2)
        template = _HEURISTIC_REASONING_TEMPLATES[seed_int % len(_HEURISTIC_REASONING_TEMPLATES)]

    reasoning = template.format(chosen=predicted_variant, other=other_variant, title=title)

    return MockEvaluationResult(
        model_name=spec.name,
        model_version=spec.version,
        predicted_variant=predicted_variant,
        confidence=confidence,
        reasoning=reasoning,
        prompt_version=PROMPT_VERSION,
        token_count=token_count,
        latency_ms=latency_ms,
        cost_usd=spec.cost_per_eval,
    )
