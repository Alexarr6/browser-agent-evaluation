from __future__ import annotations

from collections.abc import Awaitable, Callable

from browser_agent_evaluation.connectors.base import (
    BrowserConnector,
    CapabilityResult,
    ConnectorSession,
    SessionRequest,
)

SessionFactory = Callable[[SessionRequest], Awaitable[ConnectorSession]]
PreflightCheck = Callable[[], Awaitable[CapabilityResult]]


class FactoryConnector(BrowserConnector):
    """Contract adapter for framework-specific session factories.

    MCP and restricted execution retain their framework implementation behind this
    boundary while the workflow orchestrator sees only the common lifecycle.
    """

    def __init__(
        self,
        *,
        connector_id: str,
        model_id: str | None,
        preflight: PreflightCheck,
        open_session: SessionFactory,
    ) -> None:
        self.id = connector_id
        self.model_id = model_id
        self._preflight = preflight
        self._open_session = open_session

    async def preflight(self) -> CapabilityResult:
        return await self._preflight()

    async def open_session(self, request: SessionRequest) -> ConnectorSession:
        return await self._open_session(request)
