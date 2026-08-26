from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from browser_agent_evaluation.configuration.loader import configuration_sha256
from browser_agent_evaluation.configuration.models import ExperimentConfiguration


@dataclass(frozen=True)
class RuntimeApprovalPlan:
    """Exact, configuration-derived facts that require owner approval before a live run."""

    configuration_sha256: str
    provider_endpoint: str
    api_key_environment: str
    browser_executable_environment: str
    headless: bool
    connector_models: tuple[tuple[str, str | None], ...]
    workflow_paths: tuple[Path, ...]
    repetitions: int
    trial_count: int
    max_total_usd: float | None
    max_run_usd: float | None
    max_tokens_per_run: int
    max_requests_per_run: int


def build_runtime_approval_plan(
    configuration: ExperimentConfiguration, *, repository_root: Path
) -> RuntimeApprovalPlan:
    """Build the live-run approval surface without reading credentials or launching a process."""
    workflow_root = repository_root / configuration.workflows.directory
    workflow_paths = tuple(sorted(workflow_root.glob("*.yaml")))
    if not workflow_paths:
        raise ValueError(f"configured workflow directory contains no YAML files: {workflow_root}")
    connector_models: list[tuple[str, str | None]] = []
    for connector_id in configuration.enabled_runner_ids:
        if connector_id == "playwright_reference":
            connector_models.append((connector_id, None))
        else:
            runner = getattr(configuration.runners, connector_id)
            connector_models.append((connector_id, runner.model))
    return RuntimeApprovalPlan(
        configuration_sha256=configuration_sha256(configuration),
        provider_endpoint=configuration.provider.endpoint,
        api_key_environment=configuration.provider.api_key_env,
        browser_executable_environment=configuration.browser.executable_path_env,
        headless=configuration.browser.headless,
        connector_models=tuple(connector_models),
        workflow_paths=workflow_paths,
        repetitions=configuration.execution.repetitions,
        trial_count=(
            len(workflow_paths) * len(connector_models) * configuration.execution.repetitions
        ),
        max_total_usd=configuration.budget.max_total_usd,
        max_run_usd=configuration.budget.max_run_usd,
        max_tokens_per_run=configuration.budget.max_tokens_per_run,
        max_requests_per_run=configuration.execution.max_requests_per_run,
    )
