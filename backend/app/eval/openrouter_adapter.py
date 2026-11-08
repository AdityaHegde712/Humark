"""OpenRouter live multimodal evaluation adapter.

Implements ADR-008: OpenRouter LLM Provider Target for frontier vision models.
Interacts with the OpenRouter chat completions API using httpx with vision input.
"""

from dataclasses import dataclass
import json
import os
import re
import time
from typing import Any

import httpx

from app.eval.prompts import PROMPT_VERSION, format_user_prompt, get_system_prompt


class OpenRouterConfigError(Exception):
    """Raised when OpenRouter configuration or API key is missing."""


class OpenRouterEvaluationError(Exception):
    """Raised when an OpenRouter API request or response parsing fails."""


@dataclass(frozen=True)
class LiveEvaluationResult:
    """Result of an evaluation from OpenRouter live multimodal model."""

    model_name: str
    model_version: str
    predicted_variant: str  # "A" or "B"
    confidence: float
    reasoning: str
    prompt_version: str
    token_count: int
    latency_ms: int
    cost_usd: float


class OpenRouterAdapter:
    """Adapter for calling vision models through OpenRouter."""

    OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        model_name: str = "google/gemini-2.0-flash-001",
        model_version: str = "live",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.model_name = model_name
        self.model_version = model_version
        self.timeout_seconds = timeout_seconds

    @property
    def api_key(self) -> str | None:
        """Fetch API key from environment."""
        key = os.environ.get("OPENROUTER_API_KEY")
        if key and key.strip():
            return key.strip()
        return None

    def is_available(self) -> bool:
        """Check if OpenRouter API key is configured."""
        return self.api_key is not None

    def evaluate(
        self,
        challenge_id: str,
        title: str,
        category: str,
        thumbnail_a_url: str,
        thumbnail_b_url: str,
    ) -> LiveEvaluationResult:
        """Call OpenRouter vision chat completion to evaluate thumbnail variants.

        Args:
            challenge_id: ID of the challenge.
            title: YouTube video title.
            category: Video category.
            thumbnail_a_url: URL or path for Thumbnail A.
            thumbnail_b_url: URL or path for Thumbnail B.

        Returns:
            LiveEvaluationResult with parsed model prediction and telemetry.

        Raises:
            OpenRouterConfigError: If OPENROUTER_API_KEY is not configured.
            OpenRouterEvaluationError: If API call fails or returns unparseable output.
        """
        api_key = self.api_key
        if not api_key:
            raise OpenRouterConfigError(
                "OPENROUTER_API_KEY environment variable is not set. "
                "Cannot perform live OpenRouter evaluation."
            )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://humark.ai",
            "X-Title": "Humark YouTube Thumbnail Benchmark",
            "Content-Type": "application/json",
        }

        system_prompt = get_system_prompt()
        user_prompt_text = format_user_prompt(
            title=title,
            category=category,
            thumbnail_a_url=thumbnail_a_url,
            thumbnail_b_url=thumbnail_b_url,
        )

        user_content: list[dict[str, Any]] = [
            {"type": "text", "text": user_prompt_text},
            {
                "type": "image_url",
                "image_url": {"url": thumbnail_a_url},
            },
            {
                "type": "image_url",
                "image_url": {"url": thumbnail_b_url},
            },
        ]

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
        }

        start_time = time.perf_counter()
        with httpx.Client(timeout=self.timeout_seconds) as client:
            try:
                response = client.post(
                    self.OPENROUTER_API_URL,
                    headers=headers,
                    json=payload,
                )
            except httpx.RequestError as exc:
                raise OpenRouterEvaluationError(
                    f"Network error during OpenRouter call: {exc}"
                ) from exc

        elapsed_ms = int(round((time.perf_counter() - start_time) * 1000))

        if response.status_code != 200:
            raise OpenRouterEvaluationError(
                f"OpenRouter API returned HTTP {response.status_code}: {response.text}"
            )

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise OpenRouterEvaluationError("OpenRouter returned empty choices list.")

        raw_content = choices[0].get("message", {}).get("content", "")
        predicted_variant, confidence, reasoning = self._parse_completion(raw_content)

        usage = data.get("usage", {})
        token_count = usage.get("total_tokens", 0)

        # Extract cost from header or fallback
        header_cost = response.headers.get("x-openrouter-cost")
        if header_cost:
            try:
                cost_usd = float(header_cost)
            except ValueError:
                cost_usd = 0.0
        else:
            cost_usd = 0.0

        return LiveEvaluationResult(
            model_name=self.model_name,
            model_version=self.model_version,
            predicted_variant=predicted_variant,
            confidence=confidence,
            reasoning=reasoning,
            prompt_version=PROMPT_VERSION,
            token_count=token_count,
            latency_ms=elapsed_ms,
            cost_usd=cost_usd,
        )

    def _parse_completion(self, content: str) -> tuple[str, float, str]:
        """Parse JSON or structured text response from model."""
        content = content.strip()
        try:
            parsed = json.loads(content)
            variant = str(parsed.get("predicted_variant", "")).strip().upper()
            confidence = float(parsed.get("confidence", 0.70))
            reasoning = str(parsed.get("reasoning", "")).strip()
            if variant in ("A", "B"):
                return variant, min(max(confidence, 0.50), 1.00), reasoning
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        # Fallback regex search if raw JSON parsing fails
        match_var = re.search(r'["\']?predicted_variant["\']?\s*:\s*["\']?([AB])["\']?', content, re.IGNORECASE)
        variant = match_var.group(1).upper() if match_var else "A"

        match_conf = re.search(r'["\']?confidence["\']?\s*:\s*([0-1](?:\.\d+)?)', content)
        confidence = float(match_conf.group(1)) if match_conf else 0.70
        confidence = min(max(confidence, 0.50), 1.00)

        match_reason = re.search(r'["\']?reasoning["\']?\s*:\s*["\']([^"\'\n]+)["\']', content)
        reasoning = match_reason.group(1).strip() if match_reason else content[:200]

        return variant, confidence, reasoning
