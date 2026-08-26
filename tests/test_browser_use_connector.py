from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from browser_agent_evaluation.agents.browser_use.usage import usage_delta
from browser_agent_evaluation.configuration.loader import load_experiment_configuration
from browser_agent_evaluation.connectors.browser_use import BrowserUseConnector
from browser_agent_evaluation.core.models import UsageEvidence

EXPERIMENT_ROOT = Path(__file__).parents[1]


def test_usage_delta_is_step_scoped() -> None:
    before = UsageEvidence(prompt_tokens=10, completion_tokens=2, request_count=1, cost_usd=0.01)
    after = UsageEvidence(prompt_tokens=25, completion_tokens=5, request_count=3, cost_usd=0.03)

    delta = usage_delta(before, after)

    assert (delta.prompt_tokens, delta.completion_tokens, delta.request_count) == (15, 3, 2)
    assert delta.cost_usd == pytest.approx(0.02)


def test_browser_use_preflight_reads_gpt_5_6_mini_from_yaml(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configuration = load_experiment_configuration(EXPERIMENT_ROOT / "experiment.yaml")
    browser = Path("/tmp/browser-evaluation-test-chromium")
    browser.touch()
    try:
        monkeypatch.setattr(os, "environ", {
            "BROWSER_EVAL_CHROMIUM": str(browser),
            "BROWSER_EVAL_BROWSER_USE_CHROMIUM": str(browser),
            "OPENAI_API_KEY": "test-key",
        })
        connector = BrowserUseConnector(configuration=configuration, run_id="test-run")

        capability = asyncio.run(connector.preflight())

        assert capability.supported
        assert connector.model_id == "gpt-5.6-luna"
    finally:
        browser.unlink(missing_ok=True)
