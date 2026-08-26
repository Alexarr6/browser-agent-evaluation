from __future__ import annotations

import asyncio

from browser_agent_evaluation.connectors.base import (
    CapabilityResult,
    CleanupResult,
    ConnectorStepResult,
)
from browser_agent_evaluation.connectors.mcp import PlaywrightMcpConnector
from browser_agent_evaluation.connectors.restricted import RestrictedConnector
from browser_agent_evaluation.models import UsageEvidence
from browser_agent_evaluation.workflow import WorkflowStepRequest


class Session:
    async def execute_step(self, request: WorkflowStepRequest) -> ConnectorStepResult:
        del request
        return ConnectorStepResult(
            action_summary=[],
            usage=UsageEvidence(
                prompt_tokens=1,
                completion_tokens=1,
                request_count=1,
                cost_usd=0.001,
            ),
        )

    async def observe(self) -> object:
        raise AssertionError("not used by connector factory test")

    async def close(self) -> CleanupResult:
        return CleanupResult(verified=True)


async def _supported() -> CapabilityResult:
    return CapabilityResult(supported=True)


async def _open(_: object) -> Session:
    return Session()


def test_mcp_and_restricted_adapters_expose_the_common_connector_contract() -> None:
    mcp = PlaywrightMcpConnector(
        model_id="openai/gpt-5.4-mini",
        preflight=_supported,
        open_session=_open,
    )
    restricted = RestrictedConnector(
        model_id="openai/gpt-5.4-mini", preflight=_supported, open_session=_open
    )

    assert asyncio.run(mcp.preflight()).supported
    assert asyncio.run(restricted.preflight()).supported
    assert (mcp.id, restricted.id) == ("playwright_mcp", "restricted")
