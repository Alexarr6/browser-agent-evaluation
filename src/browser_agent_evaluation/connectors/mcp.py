from __future__ import annotations

from browser_agent_evaluation.connectors.factory import (
    FactoryConnector,
    PreflightCheck,
    SessionFactory,
)


class PlaywrightMcpConnector(FactoryConnector):
    """Common-lifecycle boundary for the isolated Playwright MCP implementation."""

    def __init__(
        self,
        *,
        model_id: str,
        preflight: PreflightCheck,
        open_session: SessionFactory,
    ) -> None:
        super().__init__(
            connector_id="playwright_mcp",
            model_id=model_id,
            preflight=preflight,
            open_session=open_session,
        )
