from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from browser_agent_evaluation.models import TaskPolicy, UsageEvidence
from browser_agent_evaluation.workflow import WorkflowStepRequest


@dataclass(frozen=True)
class CapabilityResult:
    supported: bool
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.supported == (self.reason is not None):
            raise ValueError("capability support and reason must agree")


@dataclass(frozen=True)
class SessionRequest:
    workflow_id: str
    start_url: str
    policy: TaskPolicy


@dataclass(frozen=True)
class ObservedPageState:
    url: str
    title: str
    visible_text: str
    input_values: dict[str, str]


@dataclass(frozen=True)
class ConnectorStepResult:
    action_summary: list[str]
    usage: UsageEvidence
    diagnostic: str | None = None


@dataclass(frozen=True)
class CleanupResult:
    verified: bool
    detail: str | None = None


class ConnectorSession(Protocol):
    async def execute_step(self, request: WorkflowStepRequest) -> ConnectorStepResult: ...

    async def observe(self) -> ObservedPageState: ...

    async def close(self) -> CleanupResult: ...


class BrowserConnector(Protocol):
    id: str
    model_id: str | None

    async def preflight(self) -> CapabilityResult: ...

    async def open_session(self, request: SessionRequest) -> ConnectorSession: ...
