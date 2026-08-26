from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from browser_agent_evaluation.connectors.base import (
    CapabilityResult,
    CleanupResult,
    ConnectorStepResult,
    ObservedPageState,
    SessionRequest,
)
from browser_agent_evaluation.models import UsageEvidence
from browser_agent_evaluation.orchestrator import WorkflowOrchestrator
from browser_agent_evaluation.workflow import WorkflowSpec, load_workflow

EXPERIMENT_ROOT = Path(__file__).parents[1]


@dataclass
class FakeSession:
    states: list[ObservedPageState]
    cleanup_verified: bool = True
    executed_steps: list[str] = field(default_factory=list)
    closed: int = 0

    async def execute_step(self, request: object) -> ConnectorStepResult:
        self.executed_steps.append(request.step_id)  # type: ignore[attr-defined]
        return ConnectorStepResult(
            action_summary=[f"executed {request.step_id}"],  # type: ignore[attr-defined]
            usage=UsageEvidence(
                prompt_tokens=1,
                completion_tokens=1,
                request_count=1,
                cost_usd=0.001,
            ),
        )

    async def observe(self) -> ObservedPageState:
        return self.states[len(self.executed_steps) - 1]

    async def close(self) -> CleanupResult:
        self.closed += 1
        return CleanupResult(verified=self.cleanup_verified)


@dataclass
class FakeConnector:
    session: FakeSession
    supported: bool = True
    id: str = "fake"
    model_id: str | None = "openai/gpt-5.4-mini"
    opened: int = 0

    async def preflight(self) -> CapabilityResult:
        return CapabilityResult(
            supported=self.supported,
            reason=None if self.supported else "missing",
        )

    async def open_session(self, request: SessionRequest) -> FakeSession:
        self.opened += 1
        assert request.workflow_id == "wikipedia-search-en"
        return self.session


def workflow() -> WorkflowSpec:
    return load_workflow(EXPERIMENT_ROOT / "tasks/workflows/en/wikipedia-search-en.yaml")


def passed_state() -> ObservedPageState:
    return ObservedPageState(
        url="https://www.wikipedia.org/wiki/Playwright",
        title="Playwright",
        visible_text="Playwright",
        input_values={},
    )


def test_orchestrator_reuses_one_session_and_records_each_step() -> None:
    session = FakeSession(states=[passed_state(), passed_state(), passed_state(), passed_state()])
    connector = FakeConnector(session=session)

    result = asyncio.run(
        WorkflowOrchestrator(configuration_sha256="a" * 64).run(
            run_id="run-1", workflow=workflow(), connector=connector
        )
    )

    assert result.receipt.outcome == "passed"
    assert session.executed_steps == ["search-playwright", "open-article", "verify-title"]
    assert session.closed == 1
    assert connector.opened == 1
    assert all(receipt.outcome == "passed" for receipt in result.receipt.step_receipts)


def test_orchestrator_stops_after_failed_step_and_still_closes() -> None:
    failed = ObservedPageState(
        url="https://www.wikipedia.org/", title="Wikipedia", visible_text="", input_values={}
    )
    session = FakeSession(states=[passed_state(), failed])

    result = asyncio.run(
        WorkflowOrchestrator(configuration_sha256="b" * 64).run(
            run_id="run-2", workflow=workflow(), connector=FakeConnector(session=session)
        )
    )

    assert result.receipt.outcome == "failed"
    assert session.executed_steps == ["search-playwright", "open-article"]
    assert session.closed == 1


def test_orchestrator_marks_unverified_cleanup_invalidated() -> None:
    session = FakeSession(
        states=[passed_state(), passed_state(), passed_state(), passed_state()],
        cleanup_verified=False,
    )

    result = asyncio.run(
        WorkflowOrchestrator(configuration_sha256="c" * 64).run(
            run_id="run-3", workflow=workflow(), connector=FakeConnector(session=session)
        )
    )

    assert result.receipt.outcome == "invalidated"
    assert result.receipt.cleanup_verified is False
