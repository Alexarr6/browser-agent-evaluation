from __future__ import annotations

import json
import re
from typing import Any, TypedDict
from urllib.parse import urlparse

from mcp import ClientSession
from mcp.types import Tool

from browser_agent_evaluation.browser.keys import normalize_key
from browser_agent_evaluation.core.models import TaskSpec
from browser_agent_evaluation.core.pricing import provider_cost_or_model_estimate

ALLOWED_MCP_TOOLS = frozenset(
    {
        "browser_navigate",
        "browser_click",
        "browser_type",
        "browser_select_option",
        "browser_press_key",
        "browser_wait_for",
        "browser_find",
        "browser_navigate_back",
        "browser_hover",
        "browser_tabs",
    }
)


class McpPilotError(RuntimeError):
    """Raised when the bounded MCP pilot violates its protocol or policy."""


class TerminalOutput(TypedDict):
    done: bool
    success: bool
    summary: str


def chat_completion_tools(tools: list[Tool]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for tool in tools:
        if tool.name not in ALLOWED_MCP_TOOLS:
            continue
        selected.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or tool.name,
                    "parameters": tool.inputSchema,
                },
            }
        )
    if {item["function"]["name"] for item in selected} != ALLOWED_MCP_TOOLS:
        raise McpPilotError("Playwright MCP tool contract is incomplete")
    return selected


def task_prompt(task: TaskSpec) -> str:
    return (
        task.instruction.strip()
        + "\n\nCompletion: "
        + task.completion
        + "\nAllowed domains: "
        + ", ".join(task.policy.allowed_domains)
    )


def assistant_message(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        message = payload["choices"][0]["message"]
    except (IndexError, KeyError, TypeError) as error:
        raise McpPilotError("provider response lacks an assistant message") from error
    if not isinstance(message, dict):
        raise McpPilotError("provider assistant message is invalid")
    return message


def provider_usage(payload: dict[str, Any], *, model: str) -> tuple[int, int, float | None]:
    try:
        usage = payload["usage"]
        prompt = usage["prompt_tokens"]
        completion = usage["completion_tokens"]
    except (KeyError, TypeError) as error:
        raise McpPilotError("provider response lacks comparable usage") from error
    if not isinstance(prompt, int) or not isinstance(completion, int):
        raise McpPilotError("provider token usage is invalid")
    return prompt, completion, provider_cost_or_model_estimate(usage, model=model)


def parse_tool_call(call: object) -> tuple[str, dict[str, Any], str]:
    if not isinstance(call, dict):
        raise McpPilotError("tool call is not an object")
    try:
        call_id = call["id"]
        function = call["function"]
        name = function["name"]
        arguments = json.loads(function["arguments"])
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise McpPilotError("tool call is malformed") from error
    if not isinstance(call_id, str) or not isinstance(name, str) or not isinstance(arguments, dict):
        raise McpPilotError("tool call fields are invalid")
    return name, arguments, call_id


def normalize_tool_arguments(*, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Normalize known model spellings to the Playwright MCP tool contract."""
    target = arguments.get("target")
    normalized = arguments
    if name == "browser_press_key" and isinstance(arguments.get("key"), str):
        normalized = {**normalized, "key": normalize_key(arguments["key"])}
    if name in ALLOWED_MCP_TOOLS and isinstance(target, str):
        match = re.fullmatch(r"ref=(e[1-9][0-9]*)", target)
        if match:
            normalized = {**normalized, "target": match.group(1)}
    regex = normalized.get("regex")
    if name == "browser_find" and isinstance(regex, str):
        match = re.fullmatch(r"/\(\?i\)(.*)/([a-z]*)", regex, flags=re.DOTALL)
        if match:
            flags = match.group(2)
            normalized = {
                **normalized,
                "regex": f"/{match.group(1)}/{flags if 'i' in flags else flags + 'i'}",
            }
    return normalized


def validate_tool_call(*, name: str, arguments: dict[str, Any], task: TaskSpec) -> None:
    if name not in ALLOWED_MCP_TOOLS:
        raise McpPilotError(f"tool is outside MCP allowlist: {name}")
    if name == "browser_navigate":
        url = arguments.get("url")
        if not isinstance(url, str) or urlparse(url).hostname not in task.policy.allowed_domains:
            raise McpPilotError("navigation is outside the task allowlist")
    if name == "browser_tabs" and arguments.get("action") == "new":
        url = arguments.get("url")
        if url is not None and (
            not isinstance(url, str) or urlparse(url).hostname not in task.policy.allowed_domains
        ):
            raise McpPilotError("new tab navigation is outside the task allowlist")


async def controller_snapshot(session: ClientSession) -> str:
    result = await session.call_tool("browser_snapshot", {"depth": 6, "boxes": False})
    text = tool_text(result)
    if result.isError:
        raise McpPilotError("controller snapshot failed: " + text[:1_000])
    return text


def terminal_output(content: object) -> TerminalOutput:
    if not isinstance(content, str):
        raise McpPilotError("model returned neither a tool call nor terminal JSON")
    try:
        value = json.loads(content)
    except json.JSONDecodeError as error:
        raise McpPilotError("terminal output is not JSON") from error
    if not isinstance(value, dict) or set(value) != {"done", "success", "summary"}:
        raise McpPilotError("terminal output has unexpected fields")
    if value["done"] is not True or not isinstance(value["success"], bool):
        raise McpPilotError("terminal status is invalid")
    if isinstance(value["summary"], dict):
        value["summary"] = json.dumps(value["summary"], ensure_ascii=False)
    if not isinstance(value["summary"], str):
        raise McpPilotError("terminal summary is invalid")
    return TerminalOutput(done=True, success=value["success"], summary=value["summary"])


def tool_text(result: object) -> str:
    content = getattr(result, "content", [])
    parts = [item.text for item in content if hasattr(item, "text") and isinstance(item.text, str)]
    return "\n".join(parts)[:20_000]


def parse_mcp_snapshot(snapshot: str) -> tuple[str, str]:
    url_match = re.search(r"^- Page URL: (.+)$", snapshot, re.MULTILINE)
    title_match = re.search(r"^- Page Title:[ \t]*(.*)$", snapshot, re.MULTILINE)
    if not url_match:
        raise McpPilotError("final MCP snapshot lacks URL")
    title = title_match.group(1).strip() if title_match else ""
    return url_match.group(1).strip(), title
