from __future__ import annotations

from collections.abc import Awaitable, Callable

from browser_agent_evaluation.connectors.base import (
    BrowserConnector,
    CapabilityResult,
    CleanupResult,
    ConnectorSession,
    ConnectorStepResult,
    ObservedPageState,
    SessionRequest,
)
from browser_agent_evaluation.workflow import WorkflowStepRequest

ReferenceStepExecutor = Callable[[WorkflowStepRequest], Awaitable[ConnectorStepResult]]
ReferenceObserver = Callable[[], Awaitable[ObservedPageState]]
ReferenceCloser = Callable[[], Awaitable[CleanupResult]]


class ReferenceConnector(BrowserConnector):
    """Connector-contract wrapper for deterministic browser execution.

    The injected callbacks let the future Playwright reference executor own browser
    operations while the workflow orchestrator owns ordering and acceptance.
    """

    id = "playwright_reference"
    model_id = None

    def __init__(
        self,
        *,
        execute_step: ReferenceStepExecutor,
        observe: ReferenceObserver,
        close: ReferenceCloser,
    ) -> None:
        self._execute_step = execute_step
        self._observe = observe
        self._close = close

    async def preflight(self) -> CapabilityResult:
        return CapabilityResult(supported=True)

    async def open_session(self, request: SessionRequest) -> ConnectorSession:
        del request
        return _ReferenceSession(self._execute_step, self._observe, self._close)


class _ReferenceSession(ConnectorSession):
    def __init__(
        self,
        execute_step: ReferenceStepExecutor,
        observe: ReferenceObserver,
        close: ReferenceCloser,
    ) -> None:
        self._execute_step = execute_step
        self._observe = observe
        self._close = close
        self._closed = False

    async def execute_step(self, request: WorkflowStepRequest) -> ConnectorStepResult:
        if self._closed:
            raise RuntimeError("reference session is already closed")
        return await self._execute_step(request)

    async def observe(self) -> ObservedPageState:
        if self._closed:
            raise RuntimeError("reference session is already closed")
        return await self._observe()

    async def close(self) -> CleanupResult:
        if self._closed:
            return CleanupResult(verified=True, detail="reference session already closed")
        self._closed = True
        return await self._close()
