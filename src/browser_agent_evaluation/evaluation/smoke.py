from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path

from browser_agent_evaluation.browser.environment import load_local_runtime_environment
from browser_agent_evaluation.configuration.loader import (
    configuration_sha256,
    load_experiment_configuration,
)
from browser_agent_evaluation.configuration.models import ExperimentConfiguration
from browser_agent_evaluation.configuration.paths import NODE_MODULES_ROOT, PROJECT_ROOT
from browser_agent_evaluation.connectors.base import (
    BrowserConnector,
    CapabilityResult,
    CleanupResult,
    ConnectorSession,
    ConnectorStepResult,
    ObservedPageState,
    SessionRequest,
)
from browser_agent_evaluation.connectors.browser_use import BrowserUseConnector
from browser_agent_evaluation.connectors.playwright_mcp import PlaywrightMcpConnector
from browser_agent_evaluation.connectors.playwright_mcp_session import PlaywrightMcpSession
from browser_agent_evaluation.connectors.restricted import RestrictedConnector
from browser_agent_evaluation.connectors.restricted_session import RestrictedSession
from browser_agent_evaluation.core.models import UsageEvidence
from browser_agent_evaluation.workflows.models import WorkflowSpec, load_workflow
from browser_agent_evaluation.workflows.orchestrator import WorkflowOrchestrator

EXPERIMENT_ROOT = PROJECT_ROOT
WORKFLOW_ROOT = PROJECT_ROOT / "tasks/workflows/en"
NODE_MODULES = NODE_MODULES_ROOT


def _reference_connector() -> BrowserConnector:
    class ReferenceSession(ConnectorSession):
        async def execute_step(self, request: object) -> ConnectorStepResult:
            del request
            return ConnectorStepResult(
                action_summary=["reference-step"],
                usage=UsageEvidence(
                    prompt_tokens=0,
                    completion_tokens=0,
                    request_count=0,
                    cost_usd=0.0,
                ),
            )

        async def observe(self) -> ObservedPageState:
            return ObservedPageState(
                url="https://www.wikipedia.org/wiki/Playwright",
                title="Playwright",
                visible_text="Playwright",
                input_values={},
            )

        async def close(self) -> CleanupResult:
            return CleanupResult(verified=True)

    class ReferenceConnector(BrowserConnector):
        id = "playwright_reference"
        model_id = None

        async def preflight(self) -> CapabilityResult:
            return CapabilityResult(supported=True)

        async def open_session(self, request: SessionRequest) -> ReferenceSession:
            del request
            return ReferenceSession()

    return ReferenceConnector()


def _mcp_connector(
    configuration: ExperimentConfiguration,
    executable: Path,
    api_key: str,
    trial_id: str,
    *,
    headless: bool,
    model_id: str,
    max_requests_per_run: int,
) -> PlaywrightMcpConnector:
    async def preflight() -> CapabilityResult:
        return CapabilityResult(supported=True)

    async def open_session(request: SessionRequest) -> PlaywrightMcpSession:
        session = PlaywrightMcpSession(
            request=request,
            api_key=api_key,
            executable=executable,
            node_modules=NODE_MODULES,
            trial_id=trial_id,
            model_id=model_id,
            max_model_requests=max_requests_per_run,
            max_total_usd=configuration.budget.max_total_usd,
            max_run_usd=configuration.budget.max_run_usd,
            max_tokens_per_run=configuration.budget.max_tokens_per_run,
            headless=headless,
        )
        await session._start()
        return session

    return PlaywrightMcpConnector(
        model_id=model_id,
        preflight=preflight,
        open_session=open_session,
    )


def _restricted_connector(
    configuration: ExperimentConfiguration,
    api_key: str,
    trial_id: str,
    *,
    headless: bool,
    model_id: str,
    max_requests_per_run: int,
) -> RestrictedConnector:
    async def preflight() -> CapabilityResult:
        return CapabilityResult(supported=True)

    async def open_session(request: SessionRequest) -> RestrictedSession:
        return await RestrictedSession.open(
            request=request,
            api_key=api_key,
            trial_id=trial_id,
            model_id=model_id,
            max_requests_per_run=max_requests_per_run,
            max_total_usd=configuration.budget.max_total_usd,
            max_run_usd=configuration.budget.max_run_usd,
            max_tokens_per_run=configuration.budget.max_tokens_per_run,
            headless=headless,
        )

    return RestrictedConnector(
        model_id=model_id,
        preflight=preflight,
        open_session=open_session,
    )


def _browser_use_connector(
    configuration: ExperimentConfiguration, trial_id: str
) -> BrowserUseConnector:
    return BrowserUseConnector(configuration=configuration, run_id=trial_id)


def _connectors(
    configuration: ExperimentConfiguration, executable: Path, api_key: str
) -> dict[str, BrowserConnector]:
    return {
        "browser_use": _browser_use_connector(
            configuration=configuration,
            trial_id=f"smoke-browser-use-{uuid.uuid4().hex[:12]}",
        ),
        "playwright_mcp": _mcp_connector(
            configuration=configuration,
            executable=executable,
            api_key=api_key,
            trial_id=f"smoke-mcp-{uuid.uuid4().hex[:12]}",
            headless=configuration.browser.headless,
            model_id=configuration.runners.playwright_mcp.model,
            max_requests_per_run=configuration.execution.max_requests_per_run,
        ),
        "restricted": _restricted_connector(
            configuration=configuration,
            api_key=api_key,
            trial_id=f"smoke-restricted-{uuid.uuid4().hex[:12]}",
            headless=configuration.browser.headless,
            model_id=configuration.runners.restricted.model,
            max_requests_per_run=configuration.execution.max_requests_per_run,
        ),
        "playwright_reference": _reference_connector(),
    }


def _workflow(configuration: ExperimentConfiguration) -> WorkflowSpec:
    return load_workflow(
        EXPERIMENT_ROOT / configuration.workflows.directory / "wikipedia-search-en.yaml"
    )


async def _smoke(configuration: ExperimentConfiguration) -> dict[str, dict[str, object]]:
    executable = Path(os.environ[configuration.browser.executable_path_env])
    api_key = os.environ[configuration.provider.api_key_env]
    receipts: dict[str, dict[str, object]] = {}
    orchestrator = WorkflowOrchestrator(
        configuration_sha256=configuration_sha256(configuration)
    )
    workflow = _workflow(configuration)
    connectors = _connectors(configuration, executable, api_key)
    for name in configuration.enabled_runner_ids:
        connector = connectors[name]
        run_id = f"{name}-{uuid.uuid4().hex[:12]}"
        result = await orchestrator.run(run_id=run_id, workflow=workflow, connector=connector)
        receipts[name] = result.receipt.model_dump(mode="json")
    return receipts


def main() -> None:
    load_local_runtime_environment(EXPERIMENT_ROOT / ".env")
    configuration = load_experiment_configuration(EXPERIMENT_ROOT / "experiment.yaml")
    output_dir = EXPERIMENT_ROOT / "evidence" / "smoke-20260824"
    output_dir.mkdir(parents=True, exist_ok=True)
    receipts = asyncio.run(_smoke(configuration))
    for name, receipt in receipts.items():
        envelope: dict[str, object] = receipt
        (output_dir / f"{name}.json").write_text(
            json.dumps(envelope, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        step_receipts: list[dict[str, object]] = envelope["step_receipts"]  # type: ignore[assignment]
        last_acceptance = step_receipts[-1]["acceptance"]
        print(name, envelope["outcome"], last_acceptance)


if __name__ == "__main__":
    main()