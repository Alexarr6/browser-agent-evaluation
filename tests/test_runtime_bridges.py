from __future__ import annotations

import json

import pytest

from browser_agent_evaluation.adapters.playwright_mcp import (
    McpToolCall,
    McpToolLoop,
    ToolScopeError,
)
from browser_agent_evaluation.adapters.stagehand import (
    NdjsonBridgeError,
    StagehandRequest,
    encode_request,
)


def test_stagehand_request_is_one_bounded_ndjson_object() -> None:
    request = StagehandRequest(
        task_id="wikipedia-search",
        procedure="Busca Playwright.",
        completion_text="La página muestra resultados.",
        allowed_domains=["en.wikipedia.org"],
        action_limit=8,
        timeout_seconds=30,
    )

    line = encode_request(request)

    assert line.endswith(b"\n")
    assert json.loads(line) == request.model_dump(mode="json")


def test_stagehand_request_rejects_oversized_bridge_message() -> None:
    request = StagehandRequest(
        task_id="task",
        procedure="x" * 200,
        completion_text="done",
        allowed_domains=["example.test"],
        action_limit=1,
        timeout_seconds=1,
    )

    with pytest.raises(NdjsonBridgeError, match="maximum"):
        encode_request(request, max_bytes=64)


def test_mcp_tool_loop_calls_only_bounded_playwright_tools() -> None:
    calls: list[McpToolCall] = []
    loop = McpToolLoop(call=lambda call: calls.append(call) or {"ok": True}, max_calls=2)

    results = loop.execute(
        [
            McpToolCall(name="playwright.navigate", arguments={"url": "https://example.test"}),
            McpToolCall(name="playwright.click", arguments={"selector": "role=button[name=Go]"}),
        ]
    )

    assert [result["ok"] for result in results] == [True, True]
    assert calls[0].name == "playwright.navigate"


def test_mcp_tool_loop_denies_non_browser_and_excess_calls() -> None:
    loop = McpToolLoop(call=lambda _: {}, max_calls=1)

    with pytest.raises(ToolScopeError, match="only Playwright"):
        loop.execute([McpToolCall(name="filesystem.read", arguments={})])
    with pytest.raises(ToolScopeError, match="call limit"):
        loop.execute(
            [
                McpToolCall(name="playwright.navigate", arguments={}),
                McpToolCall(name="playwright.click", arguments={}),
            ]
        )
