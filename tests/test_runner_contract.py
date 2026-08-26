from __future__ import annotations

import pytest

from browser_agent_evaluation.adapters.base import (
    AdapterCapabilities,
    AdapterConfiguration,
    AdapterContractError,
    validate_adapter_configuration,
)
from browser_agent_evaluation.providers.openai import (
    COMMON_MODEL,
    COMMON_PROVIDER,
    OPENROUTER_ENDPOINT,
)


def configuration(**overrides: object) -> AdapterConfiguration:
    values: dict[str, object] = {
        "runner": "browser_use",
        "provider": COMMON_PROVIDER,
        "model": COMMON_MODEL,
        "endpoint": OPENROUTER_ENDPOINT,
        "headless": True,
        "fresh_profile": True,
        "cleanup_evidence_required": True,
    }
    values.update(overrides)
    return AdapterConfiguration.model_validate(values)


def test_adapter_requires_common_model_usage_and_cleanup_capabilities() -> None:
    capabilities = AdapterCapabilities(
        supports_common_model=True,
        reports_usage=True,
        reports_cleanup=True,
        observation_mode="framework_owned",
    )

    validate_adapter_configuration(configuration(), capabilities)


@pytest.mark.parametrize(
    "capabilities",
    [
        AdapterCapabilities(
            supports_common_model=False,
            reports_usage=True,
            reports_cleanup=True,
            observation_mode="framework_owned",
        ),
        AdapterCapabilities(
            supports_common_model=True,
            reports_usage=False,
            reports_cleanup=True,
            observation_mode="framework_owned",
        ),
        AdapterCapabilities(
            supports_common_model=True,
            reports_usage=True,
            reports_cleanup=False,
            observation_mode="framework_owned",
        ),
    ],
)
def test_adapter_fails_closed_when_comparison_evidence_is_missing(
    capabilities: AdapterCapabilities,
) -> None:
    with pytest.raises(AdapterContractError):
        validate_adapter_configuration(configuration(), capabilities)


def test_adapter_rejects_non_headless_or_persistent_profile() -> None:
    capabilities = AdapterCapabilities(
        supports_common_model=True,
        reports_usage=True,
        reports_cleanup=True,
        observation_mode="framework_owned",
    )

    with pytest.raises(AdapterContractError, match="headless"):
        validate_adapter_configuration(configuration(headless=False), capabilities)
    with pytest.raises(AdapterContractError, match="fresh browser profile"):
        validate_adapter_configuration(configuration(fresh_profile=False), capabilities)
