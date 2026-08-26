from __future__ import annotations

import asyncio

import httpx

from browser_agent_evaluation.core.budget import ModelBudget
from browser_agent_evaluation.core.models import TaskSpec
from browser_agent_evaluation.providers.openai import OpenRouterPlanner


def test_openrouter_planner_requests_strict_json_and_records_usage() -> None:
    asyncio.run(_run_planner_test())


async def _run_planner_test() -> None:
    seen: dict[str, object] = {}

    def respond(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["authorization"] = request.headers["authorization"]
        seen["payload"] = request.json() if hasattr(request, "json") else request.content
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": '{"step_index":1,"step_status":"complete"}'}}
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 4, "cost": 0.01},
            },
        )

    task = TaskSpec.model_validate(
        {
            "schema_version": 1,
            "id": "wikipedia-search",
            "start_url": "https://www.wikipedia.org/",
            "instruction": "Busca Playwright y abre el artículo.",
            "completion": "Artículo abierto.",
            "policy": {"allowed_domains": ["www.wikipedia.org"], "risk": "read_only"},
            "max_actions": 12,
            "timeout_seconds": 60,
            "acceptance": {"page_title": "Playwright"},
        }
    )
    budget = ModelBudget(max_total_usd=5, max_trial_usd=0.25, max_requests_per_trial=3)
    budget.start_trial("trial-1")
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        planner = OpenRouterPlanner(
            api_key="secret", budget=budget, trial_id="trial-1", client=client
        )
        proposal = await planner.propose(
            task=task, observation="Wikipedia", action_history=(), remaining_actions=12
        )

    assert proposal.step_status == "complete"
    assert seen["url"] == "https://api.openai.com/v1/chat/completions"
    assert seen["authorization"] == "Bearer secret"
    assert planner.usage.cost_usd == 0.01
    assert planner.usage.request_count == 1
