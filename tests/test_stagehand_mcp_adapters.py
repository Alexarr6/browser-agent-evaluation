from __future__ import annotations

import pytest

from browser_agent_evaluation.adapters.base import AdapterCapabilities, AdapterConfiguration
from browser_agent_evaluation.adapters.playwright_mcp import PlaywrightMcpAdapter, ToolScopeError
from browser_agent_evaluation.adapters.stagehand import StagehandAdapter
from browser_agent_evaluation.providers.chat_completions import (
    DEFAULT_MODEL,
)

TEST_PROVIDER_ENDPOINT = "https://provider.example/v1"


def configuration(runner: str) -> AdapterConfiguration:
    return AdapterConfiguration.model_validate(
        {
            "runner": runner,
            "provider": "direct-openai",
            "model": DEFAULT_MODEL,
            "endpoint": TEST_PROVIDER_ENDPOINT,
            "headless": True,
            "fresh_profile": True,
            "cleanup_evidence_required": True,
        }
    )


def capabilities(mode: str) -> AdapterCapabilities:
    return AdapterCapabilities(
        supports_common_model=True,
        reports_usage=True,
        reports_cleanup=True,
        observation_mode=mode,  # type: ignore[arg-type]
    )


def test_stagehand_bridge_preflight_requires_stagehand_runner() -> None:
    adapter = StagehandAdapter(capabilities("framework_owned"))

    adapter.preflight(configuration("stagehand"))
    with pytest.raises(ValueError, match="stagehand"):
        adapter.preflight(configuration("browser_use"))


def test_playwright_mcp_allows_only_browser_tool_namespace() -> None:
    adapter = PlaywrightMcpAdapter(capabilities("mcp_accessibility"))

    adapter.preflight(configuration("playwright_mcp"), ["playwright.navigate", "playwright.click"])
    with pytest.raises(ToolScopeError, match="only Playwright"):
        adapter.preflight(configuration("playwright_mcp"), ["filesystem.read"])
