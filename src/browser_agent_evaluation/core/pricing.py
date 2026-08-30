"""Documented, deterministic model-price estimates independent of transport."""

from __future__ import annotations

from typing import Any

# OpenAI API pricing, Standard tier, USD per 1M tokens. Source consulted 2026-08-25:
# https://developers.openai.com/api/docs/pricing (GPT-5.6 Luna table).
LUNA_INPUT_USD_PER_MILLION = 0.40
LUNA_CACHED_INPUT_USD_PER_MILLION = 0.04
LUNA_OUTPUT_USD_PER_MILLION = 1.80


def estimate_luna_standard_cost(usage: dict[str, Any]) -> float | None:
    """Estimate a direct OpenAI request cost from its reported token usage.

    OpenAI's Chat Completions response does not include a USD cost. Cached input
    tokens receive the documented cached-input rate; all other prompt tokens use
    the normal input rate. The estimate covers standard-tier token billing only.
    """
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    if not isinstance(prompt, int) or prompt < 0:
        return None
    if not isinstance(completion, int) or completion < 0:
        return None
    details = usage.get("prompt_tokens_details")
    cached = details.get("cached_tokens", 0) if isinstance(details, dict) else 0
    if not isinstance(cached, int) or not 0 <= cached <= prompt:
        return None
    return (
        (prompt - cached) * LUNA_INPUT_USD_PER_MILLION
        + cached * LUNA_CACHED_INPUT_USD_PER_MILLION
        + completion * LUNA_OUTPUT_USD_PER_MILLION
    ) / 1_000_000


def provider_cost_or_model_estimate(usage: dict[str, Any], *, model: str) -> float | None:
    """Prefer reported cost; otherwise use a documented estimate for a known model."""
    cost = usage.get("cost")
    if isinstance(cost, int | float) and cost >= 0:
        return float(cost)
    if model == "gpt-5.6-luna":
        return estimate_luna_standard_cost(usage)
    return None
