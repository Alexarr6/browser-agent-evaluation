from __future__ import annotations

import asyncio

from browser_agent_evaluation.budget import BudgetExceeded
from browser_agent_evaluation.models import BrowserActionProposal, TaskSpec
from browser_agent_evaluation.restricted_agent import RestrictedBrowserAgent


class FakeBrowser:
    async def observe(self) -> str:
        return "safe observation"


class ExhaustedPlanner:
    async def propose(self, **_: object) -> BrowserActionProposal:
        raise BudgetExceeded("trial request cap reached")


def test_restricted_agent_records_planner_budget_exhaustion() -> None:
    task = TaskSpec.model_validate(
        {
            "schema_version": 1,
            "id": "wikipedia-search",
            "start_url": "https://www.wikipedia.org/",
            "instruction": "Busca Playwright y abre el artículo principal.",
            "completion": "La página final muestra el artículo solicitado.",
            "policy": {"allowed_domains": ["www.wikipedia.org"], "risk": "read_only"},
            "max_actions": 12,
            "timeout_seconds": 60,
            "acceptance": {"page_title": "Playwright"},
        }
    )

    outcome = asyncio.run(RestrictedBrowserAgent(ExhaustedPlanner()).run(task, FakeBrowser()))

    assert outcome.action_count == 0
    assert outcome.terminal_reason == "planner_budget_exceeded"
    assert outcome.proposal_history == ()
