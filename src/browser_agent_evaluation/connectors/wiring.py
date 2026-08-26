from __future__ import annotations

import os
from pathlib import Path

from browser_agent_evaluation.connectors.base import CapabilityResult, SessionRequest
from browser_agent_evaluation.connectors.playwright_mcp import PlaywrightMcpConnector
from browser_agent_evaluation.connectors.playwright_mcp_session import PlaywrightMcpSession
from browser_agent_evaluation.connectors.restricted import RestrictedConnector
from browser_agent_evaluation.connectors.restricted_session import RestrictedSession
from browser_agent_evaluation.core.models import TaskPolicy


class ConnectorConfiguration:
    def __init__(
        self,
        *,
        model_id: str,
        api_key_env: str,
        browser_env: str,
        node_modules: Path,
    ) -> None:
        self.model_id = model_id
        self.api_key_env = api_key_env
        self.browser_env = browser_env
        self.node_modules = node_modules

    def api_key(self) -> str:
        value = os.environ.get(self.api_key_env)
        if not value:
            raise RuntimeError(f"missing environment variable {self.api_key_env}")
        return value

    def browser_executable(self) -> Path:
        value = os.environ.get(self.browser_env)
        if not value:
            raise RuntimeError(f"missing environment variable {self.browser_env}")
        path = Path(value)
        if not path.is_file():
            raise RuntimeError(f"browser executable is not a file: {value}")
        return path


def mcp_connector(
    configuration: ConnectorConfiguration, *, trial_id: str
) -> PlaywrightMcpConnector:
    async def preflight() -> CapabilityResult:
        if not configuration.api_key_env or not os.environ.get(configuration.api_key_env):
            return CapabilityResult(False, "provider credential is unavailable")
        if not configuration.browser_env or not os.environ.get(configuration.browser_env):
            return CapabilityResult(False, "configured browser executable is unavailable")
        return CapabilityResult(True)

    async def open_session(request: SessionRequest) -> PlaywrightMcpSession:
        session = PlaywrightMcpSession(
            request=request,
            api_key=configuration.api_key(),
            executable=configuration.browser_executable(),
            node_modules=configuration.node_modules,
            trial_id=trial_id,
        )
        await session._start()
        return session

    return PlaywrightMcpConnector(
        model_id=configuration.model_id,
        preflight=preflight,
        open_session=open_session,
    )


def restricted_connector(
    configuration: ConnectorConfiguration, *, trial_id: str
) -> RestrictedConnector:
    async def preflight() -> CapabilityResult:
        if not configuration.api_key_env or not os.environ.get(configuration.api_key_env):
            return CapabilityResult(False, "provider credential is unavailable")
        return CapabilityResult(True)

    async def open_session(request: SessionRequest) -> RestrictedSession:
        return await RestrictedSession.open(
            request=request,
            api_key=configuration.api_key(),
            trial_id=trial_id,
        )

    return RestrictedConnector(
        model_id=configuration.model_id,
        preflight=preflight,
        open_session=open_session,
    )


def task_policy(*, allowed_domains: list[str], allow_form_submit: bool) -> TaskPolicy:
    return TaskPolicy(
        allowed_domains=allowed_domains,
        risk="synthetic_form" if allow_form_submit else "read_only",
        allow_form_submit=allow_form_submit,
    )