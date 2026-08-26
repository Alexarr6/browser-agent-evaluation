from __future__ import annotations

import pytest

from browser_agent_evaluation.models import UsageEvidence
from browser_agent_evaluation.provider import (
    COMMON_MODEL,
    COMMON_PROVIDER,
    OPENROUTER_ENDPOINT,
    ProviderConfiguration,
    ProviderContractError,
    require_comparable_usage,
)


def test_common_provider_configuration_is_pinned_to_openrouter_gpt_5_6_mini() -> None:
    configuration = ProviderConfiguration(
        provider=COMMON_PROVIDER,
        model=COMMON_MODEL,
        endpoint=OPENROUTER_ENDPOINT,
    )

    assert configuration.model == "gpt-5.6-luna"


@pytest.mark.parametrize(
    ("model", "endpoint"),
    [
        ("openai/gpt-5.6-mini", OPENROUTER_ENDPOINT),
        (COMMON_MODEL, "https://openrouter.ai/api/v1"),
    ],
)
def test_provider_configuration_rejects_non_equivalent_model_or_endpoint(
    model: str, endpoint: str
) -> None:
    with pytest.raises(ProviderContractError):
        ProviderConfiguration(provider=COMMON_PROVIDER, model=model, endpoint=endpoint)


def test_comparable_usage_requires_provider_reported_tokens_and_cost() -> None:
    complete = UsageEvidence(prompt_tokens=10, completion_tokens=2, request_count=1, cost_usd=0.01)
    require_comparable_usage(complete)

    unavailable = UsageEvidence(
        request_count=1, unavailable_reason="framework does not expose usage"
    )
    with pytest.raises(ProviderContractError, match="usage"):
        require_comparable_usage(unavailable)
