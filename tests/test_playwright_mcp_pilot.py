from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from browser_agent_evaluation.agents.playwright_mcp.runner import PlaywrightMcpPilot
from browser_agent_evaluation.agents.playwright_mcp.tools import (
    McpPilotError,
    normalize_tool_arguments,
    openrouter_tools,
    parse_mcp_snapshot,
    validate_tool_call,
)
from browser_agent_evaluation.core.budget import ModelBudget
from browser_agent_evaluation.evaluation.tasks import load_task


def test_tool_projection_exposes_only_bounded_browser_tools() -> None:
    names = [
        "browser_navigate",
        "browser_snapshot",
        "browser_click",
        "browser_type",
        "browser_select_option",
        "browser_press_key",
        "browser_wait_for",
        "browser_find",
        "browser_navigate_back",
        "browser_hover",
        "browser_tabs",
        "browser_evaluate",
        "browser_run_code_unsafe",
        "browser_file_upload",
    ]
    tools = [
        SimpleNamespace(
            name=name,
            description=name,
            inputSchema={
                "type": "object",
                "properties": (
                    {
                        "filename": {"type": "string"},
                        "target": {"type": "string"},
                    }
                    if name == "browser_snapshot"
                    else {}
                ),
            },
        )
        for name in names
    ]

    projected = openrouter_tools(tools)  # type: ignore[arg-type]

    projected_names = {item["function"]["name"] for item in projected}
    assert "browser_snapshot" not in projected_names
    assert "browser_evaluate" not in projected_names
    assert "browser_run_code_unsafe" not in projected_names
    assert "browser_file_upload" not in projected_names
    assert len(projected_names) == 10


def test_controller_supplies_snapshots_without_exposing_snapshot_tool() -> None:
    async def run() -> None:
        requests: list[dict[str, object]] = []
        responses = [
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "type": "function",
                                    "function": {
                                        "name": "browser_click",
                                        "arguments": '{"target":"e1"}',
                                    },
                                }
                            ],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2, "cost": 0.001},
            },
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": (
                                '{"done":true,"success":true,"summary":"complete"}'
                            ),
                        }
                    }
                ],
                "usage": {"prompt_tokens": 11, "completion_tokens": 3, "cost": 0.001},
            },
        ]

        async def responder(request: httpx.Request) -> httpx.Response:
            requests.append(json.loads(request.content))
            return httpx.Response(200, json=responses[len(requests) - 1], request=request)

        class FakeSession:
            def __init__(self) -> None:
                self.calls: list[str] = []

            async def call_tool(
                self, name: str, arguments: dict[str, object]
            ) -> SimpleNamespace:
                self.calls.append(name)
                if name == "browser_snapshot":
                    text = (
                        "### Page state\n"
                        "- Page URL: https://en.wikipedia.org/wiki/Playwright\n"
                        "- Page Title: Playwright - Wikipedia\n"
                    )
                else:
                    text = "ok"
                return SimpleNamespace(isError=False, content=[SimpleNamespace(text=text)])

        task = load_task(Path(__file__).parents[1] / "tasks/wikipedia-search.yaml")
        tools = [
            SimpleNamespace(name=name, description=name, inputSchema={"type": "object"})
            for name in [
                "browser_navigate",
                "browser_snapshot",
                "browser_click",
                "browser_type",
                "browser_select_option",
                "browser_press_key",
                "browser_wait_for",
                "browser_find",
                "browser_navigate_back",
                "browser_hover",
                "browser_tabs",
            ]
        ]
        budget = ModelBudget(max_total_usd=5, max_trial_usd=0.25, max_requests_per_trial=6)
        budget.start_trial("trial")
        session = FakeSession()
        async with httpx.AsyncClient(transport=httpx.MockTransport(responder)) as client:
            result = await PlaywrightMcpPilot(
                api_key="secret", client=client, budget=budget, trial_id="trial"
            ).run(
                task=task,
                session=session,  # type: ignore[arg-type]
                available_tools=tools,  # type: ignore[arg-type]
            )

        assert result.done is True
        assert result.action_count == 1
        assert session.calls == [
            "browser_navigate",
            "browser_snapshot",
            "browser_click",
            "browser_snapshot",
            "browser_snapshot",
        ]
        assert requests[0]["reasoning_effort"] == "none"  # type: ignore[index]
        assert requests[0]["parallel_tool_calls"] is False  # type: ignore[index]
        exposed = {tool["function"]["name"] for tool in requests[0]["tools"]}  # type: ignore[index]
        assert "browser_snapshot" not in exposed

    asyncio.run(run())


def test_mcp_normalizes_only_exact_alpha_accessibility_refs() -> None:
    assert normalize_tool_arguments(
        name="browser_type", arguments={"target": "ref=e3", "text": "Ada"}
    ) == {"target": "e3", "text": "Ada"}
    assert normalize_tool_arguments(
        name="browser_type", arguments={"target": "ref=unsafe"}
    ) == {"target": "ref=unsafe"}
    assert normalize_tool_arguments(
        name="browser_navigate", arguments={"url": "https://example.test"}
    ) == {"url": "https://example.test"}


def test_mcp_recovers_from_a_stale_tool_target() -> None:
    async def run() -> None:
        responses = [
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "type": "function",
                                    "function": {
                                        "name": "browser_click",
                                        "arguments": '{"target":"e999"}',
                                    },
                                }
                            ],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2, "cost": 0.001},
            },
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"done":true,"success":true,"summary":"complete"}',
                        }
                    }
                ],
                "usage": {"prompt_tokens": 11, "completion_tokens": 3, "cost": 0.001},
            },
        ]
        request_count = 0
        progress: list[str] = []

        async def responder(request: httpx.Request) -> httpx.Response:
            nonlocal request_count
            response = responses[request_count]
            request_count += 1
            return httpx.Response(200, json=response, request=request)

        class FakeSession:
            async def call_tool(
                self, name: str, arguments: dict[str, object]
            ) -> SimpleNamespace:
                if name == "browser_snapshot":
                    return SimpleNamespace(
                        isError=False,
                        content=[
                            SimpleNamespace(
                                text="- Page URL: https://en.wikipedia.org/wiki/Playwright\n"
                            )
                        ],
                    )
                if name == "browser_click":
                    return SimpleNamespace(
                        isError=True, content=[SimpleNamespace(text="stale target")]
                    )
                return SimpleNamespace(isError=False, content=[SimpleNamespace(text="ok")])

        task = load_task(Path(__file__).parents[1] / "tasks/wikipedia-search.yaml")
        tools = [
            SimpleNamespace(name=name, description=name, inputSchema={"type": "object"})
            for name in [
                "browser_navigate",
                "browser_snapshot",
                "browser_click",
                "browser_type",
                "browser_select_option",
                "browser_press_key",
                "browser_wait_for",
                "browser_find",
                "browser_navigate_back",
                "browser_hover",
                "browser_tabs",
            ]
        ]
        budget = ModelBudget(max_total_usd=5, max_trial_usd=0.25, max_requests_per_trial=6)
        budget.start_trial("trial")
        async with httpx.AsyncClient(transport=httpx.MockTransport(responder)) as client:
            result = await PlaywrightMcpPilot(
                api_key="secret",
                client=client,
                budget=budget,
                trial_id="trial",
                progress=progress.append,
            ).run(task=task, session=FakeSession(), available_tools=tools)  # type: ignore[arg-type]

        assert result.done is True
        assert result.successful is True
        assert result.action_count == 1
        assert any("bounded recovery" in message for message in progress)

    asyncio.run(run())


def test_mcp_retries_provider_rate_limits_with_terminal_status() -> None:
    async def run() -> None:
        calls = 0
        progress: list[str] = []

        async def responder(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                return httpx.Response(
                    429,
                    json={"error": {"message": "Please try again in 0s."}},
                    request=request,
                )
            return httpx.Response(200, json={"choices": [], "usage": {}}, request=request)

        budget = ModelBudget(max_total_usd=5, max_trial_usd=0.25, max_requests_per_trial=6)
        async with httpx.AsyncClient(transport=httpx.MockTransport(responder)) as client:
            pilot = PlaywrightMcpPilot(
                api_key="secret",
                client=client,
                budget=budget,
                trial_id="trial",
                progress=progress.append,
            )
            payload = await pilot._request(messages=[], tools=[])

        assert payload == {"choices": [], "usage": {}}
        assert calls == 2
        assert any("rate limited" in message for message in progress)

    asyncio.run(run())


def test_mcp_normalizes_python_style_case_insensitive_regex() -> None:
    assert normalize_tool_arguments(
        name="browser_find", arguments={"regex": "/(?i)(coffee|café).*beans/"}
    ) == {"regex": "/(coffee|café).*beans/i"}


def test_navigation_rejects_domain_outside_task_policy() -> None:
    task = load_task(Path(__file__).parents[1] / "tasks/wikipedia-search.yaml")

    with pytest.raises(McpPilotError, match="outside"):
        validate_tool_call(
            name="browser_navigate", arguments={"url": "https://example.com"}, task=task
        )


def test_new_mcp_tab_navigation_rejects_domain_outside_task_policy() -> None:
    task = load_task(Path(__file__).parents[1] / "tasks/wikipedia-search.yaml")

    with pytest.raises(McpPilotError, match="outside"):
        validate_tool_call(
            name="browser_tabs",
            arguments={"action": "new", "url": "https://example.com"},
            task=task,
        )


def test_snapshot_parser_accepts_empty_page_title() -> None:
    snapshot = """### Page
- Page URL: https://www.selenium.dev/selenium/web/ajaxy_page.html
### Snapshot:
```yaml
- text: Lovelace
```
"""

    assert parse_mcp_snapshot(snapshot) == (
        "https://www.selenium.dev/selenium/web/ajaxy_page.html",
        "",
    )


def test_snapshot_parser_extracts_independent_page_state() -> None:
    snapshot = """### Page state
- Page URL: https://en.wikipedia.org/wiki/Playwright
- Page Title: Playwright - Wikipedia
- Page Snapshot:
```yaml
- heading \"Playwright\"
```
"""

    assert parse_mcp_snapshot(snapshot) == (
        "https://en.wikipedia.org/wiki/Playwright",
        "Playwright - Wikipedia",
    )
