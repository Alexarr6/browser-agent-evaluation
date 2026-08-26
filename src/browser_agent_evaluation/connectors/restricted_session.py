from __future__ import annotations

from dataclasses import dataclass, field

import httpx
from playwright.async_api import Browser, Page, Playwright, async_playwright

from browser_agent_evaluation.budget import ModelBudget
from browser_agent_evaluation.connectors.base import (
    CleanupResult,
    ConnectorSession,
    ConnectorStepResult,
    ObservedPageState,
    SessionRequest,
)
from browser_agent_evaluation.live_playwright import (
    LivePlaywrightController,
    restrict_page_network,
)
from browser_agent_evaluation.models import BrowserActionProposal, TaskSpec, UsageEvidence
from browser_agent_evaluation.provider import COMMON_MODEL, OpenRouterPlanner
from browser_agent_evaluation.restricted_agent import AgentOutcome, RestrictedBrowserAgent
from browser_agent_evaluation.workflow import WorkflowStepRequest


@dataclass
class RestrictedSession(ConnectorSession):
    """One persistent restricted browser session per workflow run.

    Uses Playwright directly so multiple workflow steps share an already-open page.
    """

    request: SessionRequest
    api_key: str
    trial_id: str
    model_id: str = COMMON_MODEL
    max_completion_tokens: int | None = None
    max_requests_per_run: int = 48
    max_total_usd: float | None = None
    max_run_usd: float | None = None
    max_tokens_per_run: int | None = None
    headless: bool = True
    budget: ModelBudget = field(init=False)
    playwright: Playwright | None = field(default=None, init=False)
    browser: Browser | None = field(default=None, init=False)
    page: Page | None = field(default=None, init=False)
    history: list[str] = field(default_factory=list, init=False)
    usage: UsageEvidence = field(
        default_factory=lambda: UsageEvidence(
            prompt_tokens=0,
            completion_tokens=0,
            request_count=0,
            cost_usd=0.0,
        ),
        init=False,
    )

    @classmethod
    async def open(
        cls,
        *,
        request: SessionRequest,
        api_key: str,
        trial_id: str,
        model_id: str = COMMON_MODEL,
        max_completion_tokens: int | None = None,
        max_requests_per_run: int = 48,
        max_total_usd: float | None = None,
        max_run_usd: float | None = None,
        max_tokens_per_run: int | None = None,
        headless: bool = True,
    ) -> RestrictedSession:
        session = cls(
            request=request,
            api_key=api_key,
            trial_id=trial_id,
            model_id=model_id,
            max_completion_tokens=max_completion_tokens,
            max_requests_per_run=max_requests_per_run,
            max_total_usd=max_total_usd,
            max_run_usd=max_run_usd,
            max_tokens_per_run=max_tokens_per_run,
            headless=headless,
        )
        await session._start()
        return session

    async def _start(self) -> None:
        self.budget = ModelBudget(
            max_total_usd=self.max_total_usd,
            max_trial_usd=self.max_run_usd,
            max_requests_per_trial=self.max_requests_per_run,
            max_tokens_per_trial=self.max_tokens_per_run,
        )
        self.budget.start_trial(self.trial_id)
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
        await restrict_page_network(
            self.page, allowed_domains=self.request.policy.allowed_domains
        )
        await self.page.goto(self.request.start_url)

    async def execute_step(self, request: WorkflowStepRequest) -> ConnectorStepResult:
        page = self.page
        if page is None:
            raise RuntimeError("restricted session is not open")
        before_usage = self.usage
        agent = RestrictedBrowserAgent(
            _Planner(
                self.api_key,
                self.budget,
                self.trial_id,
                model=self.model_id,
                max_completion_tokens=self.max_completion_tokens,
            )
        )
        task = TaskSpec(
            schema_version=1,
            id=f"{self.trial_id}-step",
            start_url=page.url,
            instruction=request.instruction,
            completion="step completed",
            policy=request.policy,
            max_actions=50,
            timeout_seconds=300,
            acceptance=_permissive_acceptance(),
        )
        history_before = len(self.history)
        outcome = await agent.run(
            task,
            LivePlaywrightController(page, allowed_domains=self.request.policy.allowed_domains),
        )
        for fingerprint in outcome.action_history[history_before:]:
            self.history.append(fingerprint)
        self.usage = agent.planner.usage  # type: ignore[attr-defined]
        return ConnectorStepResult(
            action_summary=list(outcome.action_history[history_before:]),
            usage=usage_delta(before_usage, self.usage),
            diagnostic=outcome.terminal_reason if not self._is_complete(outcome) else None,
        )

    async def observe(self) -> ObservedPageState:
        page = self.page
        if page is None:
            raise RuntimeError("restricted session is not open")
        url = page.url
        title = await page.title()
        text = (await page.locator("body").inner_text())[:20_000]
        return ObservedPageState(
            url=url,
            title=title,
            visible_text=text,
            input_values={},
        )

    async def close(self) -> CleanupResult:
        browser = self.browser
        playwright = self.playwright
        try:
            if browser is not None:
                await browser.close()
            if playwright is not None:
                await playwright.stop()
        finally:
            self.browser = None
            self.playwright = None
            self.page = None
        return CleanupResult(verified=True, detail="restricted session force-closed")

    @staticmethod
    def _is_complete(outcome: AgentOutcome) -> bool:
        return outcome.terminal_reason == "complete"


class _Planner:
    def __init__(
        self,
        api_key: str,
        budget: ModelBudget,
        trial_id: str,
        *,
        model: str,
        max_completion_tokens: int | None,
    ) -> None:
        self._api_key = api_key
        self._budget = budget
        self._trial_id = trial_id
        self._model = model
        self._max_completion_tokens = max_completion_tokens
        self._client = httpx.AsyncClient()
        self._planner = OpenRouterPlanner(
            api_key=api_key,
            budget=budget,
            trial_id=trial_id,
            client=self._client,
            model=model,
            max_completion_tokens=max_completion_tokens,
        )
        self.usage = UsageEvidence(
            prompt_tokens=None,
            completion_tokens=None,
            request_count=0,
            cost_usd=None,
            unavailable_reason="restricted session did not issue model requests",
        )

    async def propose(
        self,
        *,
        task: object,
        observation: str,
        action_history: tuple[str, ...],
        remaining_actions: int,
    ) -> BrowserActionProposal:
        proposal = await self._planner.propose(
            task=task,  # type: ignore[arg-type]
            observation=observation,
            action_history=action_history,
            remaining_actions=remaining_actions,
        )
        self.usage = self._planner.usage
        return proposal


def _permissive_acceptance() -> object:
    from browser_agent_evaluation.models import AcceptanceSpec

    return AcceptanceSpec(page_title=" ")


def usage_delta(before: UsageEvidence, after: UsageEvidence) -> UsageEvidence:
    if before.unavailable_reason or after.unavailable_reason:
        return UsageEvidence(
            prompt_tokens=None,
            completion_tokens=None,
            request_count=after.request_count - before.request_count,
            cost_usd=None,
            unavailable_reason=after.unavailable_reason or before.unavailable_reason,
        )
    assert before.prompt_tokens is not None and after.prompt_tokens is not None
    assert before.completion_tokens is not None and after.completion_tokens is not None
    assert before.cost_usd is not None and after.cost_usd is not None
    return UsageEvidence(
        prompt_tokens=after.prompt_tokens - before.prompt_tokens,
        completion_tokens=after.completion_tokens - before.completion_tokens,
        request_count=after.request_count - before.request_count,
        cost_usd=after.cost_usd - before.cost_usd,
    )


__all__ = ["RestrictedSession", "COMMON_MODEL"]