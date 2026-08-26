from __future__ import annotations

import json
import subprocess

import pytest

from browser_agent_evaluation.browser_use_openrouter import _response_diagnostic
from browser_agent_evaluation.browser_use_pilot import (
    BrowserUsePilotError,
    _block_external_browser_launch,
)
from browser_agent_evaluation.models import UsageEvidence
from browser_agent_evaluation.provider import COMMON_MODEL, COMMON_PROVIDER, OPENROUTER_ENDPOINT
from browser_agent_evaluation.runners.base import (
    AdapterCapabilities,
    AdapterConfiguration,
    AdapterContractError,
)
from browser_agent_evaluation.runners.browser_use import BrowserUseAdapter


def configuration() -> AdapterConfiguration:
    return AdapterConfiguration(
        runner="browser_use",
        provider=COMMON_PROVIDER,
        model=COMMON_MODEL,
        endpoint=OPENROUTER_ENDPOINT,
        headless=True,
        fresh_profile=True,
        cleanup_evidence_required=True,
    )


def test_json_failure_diagnostic_preserves_finish_reason_and_bounded_tail() -> None:
    content = "x" * 1_100
    diagnostic = json.loads(
        _response_diagnostic(
            event="invalid_json",
            content=content,
            finish_reason="length",
            error=ValueError("unterminated JSON"),
        )
    )

    assert diagnostic == {
        "browser_use_adapter_event": "invalid_json",
        "content_characters": 1_100,
        "finish_reason": "length",
        "parse_error": "unterminated JSON",
        "content_tail": "x" * 1_000,
    }


def test_browser_use_failure_retains_usage_and_cleanup_evidence() -> None:
    usage = UsageEvidence(
        prompt_tokens=10,
        completion_tokens=2,
        request_count=1,
        cost_usd=0.001,
    )

    error = BrowserUsePilotError(
        "final state unavailable", usage=usage, trace="bounded trace", cleanup_verified=True
    )

    assert error.usage == usage
    assert error.trace == "bounded trace"
    assert error.cleanup_verified is True


def test_external_browser_launcher_is_blocked_locally() -> None:
    with _block_external_browser_launch() as log:
        result = subprocess.run(["xdg-open", "https://example.test"], check=False)
        captured = log.read_text(encoding="utf-8")

    assert result.returncode == 126
    assert captured == "https://example.test\n"


def test_browser_use_preflight_accepts_only_comparable_capabilities() -> None:
    adapter = BrowserUseAdapter(
        AdapterCapabilities(
            supports_common_model=True,
            reports_usage=True,
            reports_cleanup=True,
            observation_mode="framework_owned",
        )
    )

    adapter.preflight(configuration())


def test_browser_use_preflight_fails_closed_without_usage() -> None:
    adapter = BrowserUseAdapter(
        AdapterCapabilities(
            supports_common_model=True,
            reports_usage=False,
            reports_cleanup=True,
            observation_mode="framework_owned",
        )
    )

    with pytest.raises(AdapterContractError, match="usage"):
        adapter.preflight(configuration())
