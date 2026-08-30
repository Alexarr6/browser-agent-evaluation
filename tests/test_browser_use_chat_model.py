from __future__ import annotations

import asyncio
import json

import httpx
from pydantic import BaseModel

from browser_agent_evaluation.agents.browser_use.model import BrowserUseChatModel
from browser_agent_evaluation.core.budget import BudgetExceeded, ModelBudget

TEST_PROVIDER_ENDPOINT = "https://provider.example/v1"


class ExampleOutput(BaseModel):
    status: str
    action: list[dict[str, object]]


def test_adapter_parses_json_object_against_requested_output_model() -> None:
    asyncio.run(_invoke('{"status":"ok","action":[{"done":{}}]}'))


def test_adapter_prompt_contains_lowercase_json_for_openai_compatibility() -> None:
    async def run() -> None:
        async def responder(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            prompt = "\n".join(
                message["content"] for message in payload["messages"] if message["role"] == "system"
            )
            assert "json" in prompt
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": '{"status":"ok","action":[]}'}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.001},
                },
                request=request,
            )

        budget = ModelBudget(max_total_usd=5.0, max_trial_usd=0.25, max_requests_per_trial=3)
        budget.start_trial("trial")
        async with httpx.AsyncClient(transport=httpx.MockTransport(responder)) as client:
            adapter = BrowserUseChatModel(
                api_key="secret",
                http_client=client,
                budget=budget,
                trial_id="trial",
                endpoint=TEST_PROVIDER_ENDPOINT,
            )
            await adapter.ainvoke([], output_format=ExampleOutput)

    asyncio.run(run())


async def _invoke(content: str) -> None:
    async def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "request-1",
                "object": "chat.completion",
                "created": 1,
                "model": "openai/gpt-5.6-luna",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": content},
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                    "cost": 0.001,
                },
            },
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(responder)) as client:
        budget = ModelBudget(max_total_usd=5.0, max_trial_usd=0.25, max_requests_per_trial=3)
        budget.start_trial("trial")
        adapter = BrowserUseChatModel(
            api_key="secret",
            http_client=client,
            budget=budget,
            trial_id="trial",
            endpoint=TEST_PROVIDER_ENDPOINT,
        )
        result = await adapter.ainvoke([], output_format=ExampleOutput)

    assert result.completion.status == "ok"
    assert result.usage is not None
    assert result.usage.prompt_tokens == 10


def test_adapter_omits_json_response_format_for_free_text_extraction() -> None:
    async def run() -> None:
        async def responder(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            assert "response_format" not in payload
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "coffee result"}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.001},
                },
                request=request,
            )

        budget = ModelBudget(max_total_usd=5.0, max_trial_usd=0.25, max_requests_per_trial=3)
        budget.start_trial("trial")
        async with httpx.AsyncClient(transport=httpx.MockTransport(responder)) as client:
            adapter = BrowserUseChatModel(
                api_key="secret",
                http_client=client,
                budget=budget,
                trial_id="trial",
                endpoint=TEST_PROVIDER_ENDPOINT,
            )
            result = await adapter.ainvoke([])

        assert result.completion == "coffee result"

    asyncio.run(run())


def test_adapter_normalizes_known_wrapper_and_singular_action() -> None:
    content = '{"agent_output":{"status":"ok","action":{"done":{}}}}'

    asyncio.run(_invoke(content))


def test_adapter_accepts_json_markdown_fence_only() -> None:
    asyncio.run(_invoke('```json\n{"status":"ok","action":[{"done":{}}]}\n```'))


def test_adapter_omits_completion_cap_when_configuration_is_unbounded() -> None:
    async def run() -> None:
        async def responder(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            assert "max_tokens" not in payload
            assert "temperature" not in payload
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": '{"status":"ok","action":[]}'}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.001},
                },
                request=request,
            )

        budget = ModelBudget(max_total_usd=5.0, max_trial_usd=0.25, max_requests_per_trial=3)
        budget.start_trial("trial")
        async with httpx.AsyncClient(transport=httpx.MockTransport(responder)) as client:
            adapter = BrowserUseChatModel(
                api_key="secret",
                http_client=client,
                budget=budget,
                trial_id="trial",
                endpoint=TEST_PROVIDER_ENDPOINT,
                max_completion_tokens=None,
            )
            result = await adapter.ainvoke([], output_format=ExampleOutput)

        assert result.completion.status == "ok"

    asyncio.run(run())


def test_adapter_checks_budget_before_provider_request() -> None:
    async def run() -> None:
        calls = 0

        async def responder(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(500, request=request)

        budget = ModelBudget(max_total_usd=5.0, max_trial_usd=0.25, max_requests_per_trial=1)
        budget.start_trial("trial")
        budget.before_request("trial")
        async with httpx.AsyncClient(transport=httpx.MockTransport(responder)) as client:
            adapter = BrowserUseChatModel(
                api_key="secret",
                http_client=client,
                budget=budget,
                trial_id="trial",
                endpoint=TEST_PROVIDER_ENDPOINT,
            )
            try:
                await adapter.ainvoke([], output_format=ExampleOutput)
            except BudgetExceeded:
                pass
            else:
                raise AssertionError("request cap must fail closed")
        assert calls == 0

    asyncio.run(run())
