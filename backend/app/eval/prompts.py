"""Versioned prompts for YouTube thumbnail comparative evaluation."""

PROMPT_VERSION = "v1.0.0"

SYSTEM_PROMPT = """You are an expert YouTube audience analyst and thumbnail strategist with deep expertise in viewer psychology, click-through-rate (CTR) optimization, visual hierarchy, and title-thumbnail pairing.

Your objective is to evaluate two alternative YouTube thumbnail designs (Variant A and Variant B) for a given video title and category, and predict which thumbnail achieved a higher CTR in real-world viewer testing.

Guidelines:
1. Carefully compare visual clarity, subject framing, emotional resonance, typography legibility, and curiosity gap.
2. Select either "A" or "B" as the winning variant.
3. Provide a confidence score between 0.50 and 1.00.
4. Provide concise, expert reasoning highlighting the deciding visual factors.
5. Format your response strictly as valid JSON:
{
  "predicted_variant": "A" | "B",
  "confidence": <float between 0.50 and 1.00>,
  "reasoning": "<concise explanation>"
}"""


def get_system_prompt() -> str:
    """Return the pinned system prompt for thumbnail comparative evaluation."""
    return SYSTEM_PROMPT


def format_user_prompt(
    title: str,
    category: str,
    thumbnail_a_url: str | None = None,
    thumbnail_b_url: str | None = None,
) -> str:
    """Format the pinned user prompt for evaluating a thumbnail A/B pair.

    Args:
        title: YouTube video title.
        category: Content category (e.g. entertainment, education, gaming).
        thumbnail_a_url: Optional URL or path for Thumbnail A.
        thumbnail_b_url: Optional URL or path for Thumbnail B.

    Returns:
        Structured user prompt string.
    """
    url_details = ""
    if thumbnail_a_url and thumbnail_b_url:
        url_details = f"\n- Variant A Image: {thumbnail_a_url}\n- Variant B Image: {thumbnail_b_url}"

    return (
        f"Video Title: {title}\n"
        f"Category: {category}\n"
        f"{url_details}\n\n"
        "Variant A: Thumbnail A\n"
        "Variant B: Thumbnail B\n\n"
        "Analyze both thumbnail variants against the title and target audience. "
        "Which thumbnail generated a higher click-through rate (CTR)? "
        "Return your answer strictly in the requested JSON format."
    )
