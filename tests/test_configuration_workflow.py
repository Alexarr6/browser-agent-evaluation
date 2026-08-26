from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from browser_agent_evaluation.configuration import (
    ExperimentConfiguration,
    configuration_sha256,
    load_experiment_configuration,
)
from browser_agent_evaluation.preflight import build_runtime_approval_plan
from browser_agent_evaluation.workflow import load_workflow

EXPERIMENT_ROOT = Path(__file__).parents[1]


def test_default_configuration_is_strict_and_hashable() -> None:
    configuration = load_experiment_configuration(EXPERIMENT_ROOT / "experiment.yaml")

    assert configuration.runners.browser_use.model == "gpt-5.6-luna"
    assert configuration.budget.max_tokens_per_run == 1_000_000
    assert configuration.runners.browser_use.completion_tokens is None
    assert configuration.execution.repetitions == 3
    assert configuration.browser.headless is False
    assert configuration.browser.executable_path_env == "BROWSER_EVAL_CHROMIUM"
    assert (
        configuration.browser.browser_use_executable_path_env
        == "BROWSER_EVAL_BROWSER_USE_CHROMIUM"
    )
    assert configuration_sha256(configuration) == configuration_sha256(configuration)


def test_configuration_can_select_every_comparable_connector() -> None:
    configuration = load_experiment_configuration(EXPERIMENT_ROOT / "experiment.yaml")

    assert configuration.enabled_runner_ids == (
        "playwright_reference",
        "restricted",
        "browser_use",
        "playwright_mcp",
    )
    assert {
        configuration.runners.restricted.model,
        configuration.runners.browser_use.model,
        configuration.runners.playwright_mcp.model,
    } == {"gpt-5.6-luna"}


def test_runtime_preflight_derives_exact_live_run_approval_facts() -> None:
    configuration = load_experiment_configuration(EXPERIMENT_ROOT / "experiment.yaml")

    plan = build_runtime_approval_plan(configuration, repository_root=EXPERIMENT_ROOT)

    assert plan.connector_models == (
        ("playwright_reference", None),
        ("restricted", "gpt-5.6-luna"),
        ("browser_use", "gpt-5.6-luna"),
        ("playwright_mcp", "gpt-5.6-luna"),
    )
    assert plan.trial_count == len(plan.workflow_paths) * 4 * 3
    assert plan.max_tokens_per_run == 1_000_000
    assert plan.max_requests_per_run == 48


def test_configuration_rejects_unknown_or_unsafe_execution_values() -> None:
    raw = yaml.safe_load((EXPERIMENT_ROOT / "experiment.yaml").read_text(encoding="utf-8"))
    raw["budget"]["max_run_usd"] = 4
    raw["unknown"] = True

    with pytest.raises(ValidationError):
        ExperimentConfiguration.model_validate(raw)


def test_workflow_hides_machine_acceptance_from_connector_request() -> None:
    workflow = load_workflow(
        EXPERIMENT_ROOT / "tasks/workflows/en/wikipedia-search-en.yaml"
    )

    request = workflow.connector_step_request(workflow.steps[0])

    assert request.instruction == "Search Wikipedia for Playwright."
    assert "acceptance" not in request.model_dump()
    assert workflow.final_acceptance.page_title == "Playwright"
    assert workflow.policy.allowed_domains == ["www.wikipedia.org", "en.wikipedia.org"]


def test_workflow_rejects_duplicate_step_ids(tmp_path: Path) -> None:
    raw = yaml.safe_load(
        (EXPERIMENT_ROOT / "tasks/workflows/en/wikipedia-search-en.yaml").read_text(
            encoding="utf-8"
        )
    )
    raw["steps"][1]["id"] = raw["steps"][0]["id"]
    path = tmp_path / "duplicate-steps.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ValidationError, match="unique"):
        load_workflow(path)
