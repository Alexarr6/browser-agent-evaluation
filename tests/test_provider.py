from __future__ import annotations

import pytest

from browser_agent_evaluation.core.models import UsageEvidence
from browser_agent_evaluation.providers.chat_completions import (
    DEFAULT_MODEL,
    ProviderConfiguration,
    ProviderContractError,
    require_comparable_usage,
)

TEST_PROVIDER_ENDPOINT = "https://provider.example/v1"


def test_provider_configuration_accepts_configured_identity_model_and_endpoint() -> None:
    configuration = ProviderConfiguration(
        provider="direct-openai",
        model=DEFAULT_MODEL,
        endpoint=TEST_PROVIDER_ENDPOINT,
    )

    assert configuration.model == "gpt-5.6-luna"


def test_provider_configuration_is_not_pinned_to_one_provider() -> None:
    configuration = ProviderConfiguration(
        provider="compatible-provider",
        model="other-model",
        endpoint="https://provider.example/v1",
    )

    assert configuration.provider == "compatible-provider"


@pytest.mark.parametrize(
    ("provider", "model", "endpoint"),
    [
        ("", DEFAULT_MODEL, TEST_PROVIDER_ENDPOINT),
        ("direct-openai", "", TEST_PROVIDER_ENDPOINT),
        ("direct-openai", DEFAULT_MODEL, "http://provider.example/v1"),
    ],
)
def test_provider_configuration_rejects_incomplete_or_insecure_values(
    provider: str, model: str, endpoint: str
) -> None:
    with pytest.raises(ProviderContractError):
        ProviderConfiguration(provider=provider, model=model, endpoint=endpoint)


def test_comparable_usage_requires_provider_reported_tokens_and_cost() -> None:
    complete = UsageEvidence(prompt_tokens=10, completion_tokens=2, request_count=1, cost_usd=0.01)
    require_comparable_usage(complete)

    unavailable = UsageEvidence(
        request_count=1, unavailable_reason="framework does not expose usage"
    )
    with pytest.raises(ProviderContractError, match="usage"):
        require_comparable_usage(unavailable)
