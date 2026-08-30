from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx

from browser_agent_evaluation.agents.browser_use.model import BrowserUseChatModel
from browser_agent_evaluation.agents.browser_use.usage import (
    ChatCompletionsUsageCapture,
    usage_delta,
)
from browser_agent_evaluation.browser.environment import BROWSER_USE_PRIVACY_OVERRIDES
from browser_agent_evaluation.configuration.models import ExperimentConfiguration
from browser_agent_evaluation.connectors.base import (
    BrowserConnector,
    CapabilityResult,
    CleanupResult,
    ConnectorSession,
    ConnectorStepResult,
    ObservedPageState,
    SessionRequest,
)
from browser_agent_evaluation.core.budget import ModelBudget
from browser_agent_evaluation.workflows.models import WorkflowStepRequest


class BrowserUseConnector(BrowserConnector):
    """browser-use connector retaining one isolated browser for one workflow run."""

    id = "browser_use"

    def __init__(self, *, configuration: ExperimentConfiguration, run_id: str) -> None:
        self._configuration = configuration
        self._run_id = run_id
        self.model_id = configuration.runners.browser_use.model

    async def preflight(self) -> CapabilityResult:
        browser = self._configuration.browser
        provider = self._configuration.provider
        if not os.environ.get(browser.browser_use_executable_path_env):
            return CapabilityResult(False, "configured browser executable is unavailable")
        if not os.environ.get(provider.api_key_env):
            return CapabilityResult(False, "configured provider credential is unavailable")
        if not self._configuration.runners.browser_use.enabled:
            return CapabilityResult(False, "browser-use is disabled in experiment configuration")
        return CapabilityResult(True)

    async def open_session(self, request: SessionRequest) -> ConnectorSession:
        executable = Path(os.environ[self._configuration.browser.browser_use_executable_path_env])
        api_key = os.environ[self._configuration.provider.api_key_env]
        if not executable.is_file():
            raise RuntimeError("configured browser executable does not exist")
        os.environ.update(BROWSER_USE_PRIVACY_OVERRIDES)
        from browser_use import Browser

        budget = ModelBudget(
            max_total_usd=self._configuration.budget.max_total_usd,
            max_trial_usd=self._configuration.budget.max_run_usd,
            max_requests_per_trial=self._configuration.execution.max_requests_per_run,
            max_tokens_per_trial=self._configuration.budget.max_tokens_per_run,
        )
        budget.start_trial(self._run_id)
        capture = ChatCompletionsUsageCapture(httpx.AsyncHTTPTransport())
        client = httpx.AsyncClient(transport=capture)
        llm = BrowserUseChatModel(
            api_key=api_key,
            http_client=client,
            budget=budget,
            trial_id=self._run_id,
            model=self.model_id,
            endpoint=self._configuration.provider.endpoint,
            max_completion_tokens=self._configuration.runners.browser_use.completion_tokens,
        )
        browser = Browser(
            executable_path=executable,
            headless=self._configuration.browser.headless,
            allowed_domains=request.policy.allowed_domains,
            keep_alive=True,
            accept_downloads=False,
            enable_default_extensions=False,
        )
        await browser.start()
        await browser.navigate_to(request.start_url)
        return _BrowserUseSession(browser=browser, client=client, llm=llm, capture=capture)


class _BrowserUseSession(ConnectorSession):
    def __init__(
        self,
        *,
        browser: Any,
        client: httpx.AsyncClient,
        llm: BrowserUseChatModel,
        capture: ChatCompletionsUsageCapture,
    ) -> None:
        self._browser = browser
        self._client = client
        self._llm = llm
        self._capture = capture
        self._closed = False

    async def execute_step(self, request: WorkflowStepRequest) -> ConnectorStepResult:
        if self._closed:
            raise RuntimeError("browser-use session is already closed")
        from browser_use import Agent, Tools

        before = self._capture.usage
        agent: Any = Agent(
            task=_step_prompt(request),
            llm=self._llm,
            browser=self._browser,
            directly_open_url=False,
            tools=Tools(
                exclude_actions=[
                    "evaluate",
                    "upload_file",
                    "read_file",
                    "write_file",
                    "replace_file",
                    "save_as_pdf",
                ]
            ),
            use_vision=False,
            use_thinking=False,
            enable_planning=False,
            use_judge=False,
            calculate_cost=False,
            enable_signal_handler=False,
        )
        # browser-use defaults to 500 steps; only the provider-cost budget and
        # framework failure handling should terminate a configured workflow.
        history = await agent.run(max_steps=2**31 - 1)
        return ConnectorStepResult(
            action_summary=[str(action) for action in history.model_actions()],
            usage=usage_delta(before, self._capture.usage),
            diagnostic=self._llm.evidence_trace if not history.is_successful() else None,
        )

    async def observe(self) -> ObservedPageState:
        if self._closed:
            raise RuntimeError("browser-use session is already closed")
        state = await self._browser.get_browser_state_summary(include_screenshot=False)
        return ObservedPageState(
            url=state.url,
            title=state.title,
            visible_text=state.dom_state.llm_representation(),
            input_values={},
        )

    async def close(self) -> CleanupResult:
        if self._closed:
            return CleanupResult(verified=True, detail="browser-use session already closed")
        self._closed = True
        try:
            await self._browser.kill()
        finally:
            await self._client.aclose()
        return CleanupResult(verified=True, detail="browser-use force kill completed")


def _step_prompt(request: WorkflowStepRequest) -> str:
    domains = ", ".join(request.policy.allowed_domains)
    return (
        "Execute only this workflow step in the already-open browser session. "
        "Do not open another browser, log in, download files, bypass CAPTCHAs, use "
        f"credentials, or leave these allowed domains: {domains}.\n\n"
        f"Step: {request.instruction}"
    )
