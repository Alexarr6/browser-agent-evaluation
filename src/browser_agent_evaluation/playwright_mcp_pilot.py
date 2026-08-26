from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypedDict
from urllib.parse import urlparse

import httpx
from mcp import ClientSession
from mcp.types import Tool

from browser_agent_evaluation.budget import ModelBudget
from browser_agent_evaluation.models import TaskSpec, UsageEvidence
from browser_agent_evaluation.pricing import provider_cost_or_luna_estimate
from browser_agent_evaluation.provider import COMMON_MODEL, OPENROUTER_ENDPOINT

ALLOWED_MCP_TOOLS = frozenset(
    {
        "browser_navigate",
        "browser_click",
        "browser_type",
        "browser_select_option",
        "browser_press_key",
        "browser_wait_for",
        # Safe discovery/navigation tools needed for open-ended web tasks.
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


@dataclass(frozen=True)
class McpPilotResult:
    done: bool
    successful: bool
    action_count: int
    final_url: str
    final_title: str
    visible_text: str
    usage: UsageEvidence
    trace: str


@dataclass
class PlaywrightMcpPilot:
    api_key: str
    client: httpx.AsyncClient
    budget: ModelBudget
    trial_id: str
    model: str = COMMON_MODEL
    max_completion_tokens: int | None = None
    max_model_requests: int = 12
    max_tool_calls: int = 24
    prompt_tokens: int = field(default=0, init=False)
    completion_tokens: int = field(default=0, init=False)
    request_count: int = field(default=0, init=False)
    cost_usd: float | None = field(default=0.0, init=False)
    action_count: int = field(default=0, init=False)
    trace_lines: list[str] = field(default_factory=list, init=False)
    progress: Callable[[str], None] | None = field(default=None, repr=False)

    @property
    def usage(self) -> UsageEvidence:
        return UsageEvidence(
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            request_count=self.request_count,
            cost_usd=self.cost_usd,
            unavailable_reason=(
                "OpenAI Chat Completions does not report per-request USD cost"
                if self.cost_usd is None
                else None
            ),
        )

    async def run(
        self, *, task: TaskSpec, session: ClientSession, available_tools: list[Tool]
    ) -> McpPilotResult:
        tools = _openrouter_tools(available_tools)
        initial = await session.call_tool("browser_navigate", {"url": task.start_url})
        if initial.isError:
            raise McpPilotError("initial MCP navigation failed: " + _tool_text(initial)[:1_000])
        initial_snapshot = await _controller_snapshot(session)
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You control a browser only through the supplied tools. Use exactly one tool "
                    "per response. A current full-page snapshot is supplied after every action; "
                    "do not request observations. browser_find regexes use JavaScript syntax "
                    "(for example /coffee.*beans/i), never Python inline flags. Never use "
                    "JavaScript, files, downloads, credentials, or domains outside the task "
                    "allowlist. When the task is "
                    "complete, return exactly "
                    '{"done":true,"success":true,"summary":"..."} with no tool call.'
                ),
            },
            {"role": "user", "content": _task_prompt(task)},
            {"role": "user", "content": "Initial browser state:\n" + initial_snapshot},
        ]
        action_count = 0
        tool_recoveries = 0
        done = False
        successful = False

        for request_index in range(self.max_model_requests):
            self._emit(f"model request {request_index + 1}/{self.max_model_requests}")
            self.budget.before_request(self.trial_id)
            payload = await self._request(messages=messages, tools=tools)
            self.request_count += 1
            prompt, completion, cost = _provider_usage(payload)
            self.budget.consume_usage(self.trial_id, cost, prompt, completion)
            self.prompt_tokens += prompt
            self.completion_tokens += completion
            self.cost_usd = None if cost is None or self.cost_usd is None else self.cost_usd + cost
            message = _assistant_message(payload)
            tool_calls = message.get("tool_calls") or []
            if tool_calls:
                if not isinstance(tool_calls, list) or len(tool_calls) != 1:
                    raise McpPilotError("model must request exactly one MCP tool per turn")
                if action_count >= self.max_tool_calls:
                    raise McpPilotError("MCP tool call cap reached")
                call = tool_calls[0]
                name, arguments, call_id = _parse_tool_call(call)
                arguments = _normalize_mcp_tool_arguments(name=name, arguments=arguments)
                _validate_tool_call(name=name, arguments=arguments, task=task)
                messages.append(message)
                self._emit(f"tool {action_count + 1}/{self.max_tool_calls}: {name}")
                result = await session.call_tool(name, arguments)
                result_text = _tool_text(result)
                if result.isError:
                    action_count += 1
                    self.action_count = action_count
                    tool_recoveries += 1
                    self.trace_lines.append(f"{name} failed: {result_text[:500]}")
                    if tool_recoveries > 2:
                        raise McpPilotError(
                            f"MCP tool recovery exhausted after {name}: {result_text[:1_000]}"
                        )
                    snapshot = await _controller_snapshot(session)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "name": name,
                            "content": (
                                "Tool error; inspect the current state and choose a "
                                "different valid action. Do not repeat the failed call.\n"
                                + result_text[:1_000]
                                + "\nCurrent browser state:\n"
                                + snapshot
                            )[-20_000:],
                        }
                    )
                    self._emit(f"tool failed; bounded recovery {tool_recoveries}/2")
                    continue
                snapshot = await _controller_snapshot(session)
                snapshot_url, _ = parse_mcp_snapshot(snapshot)
                if urlparse(snapshot_url).hostname not in task.policy.allowed_domains:
                    raise McpPilotError("browser action navigated outside the task allowlist")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": name,
                        "content": (result_text + "\nCurrent browser state:\n" + snapshot)[
                            -20_000:
                        ],
                    }
                )
                action_count += 1
                self.action_count = action_count
                self.trace_lines.append(f"{name} {json.dumps(arguments, sort_keys=True)}")
                continue
            content = message.get("content")
            terminal = _terminal_output(content)
            done = terminal["done"]
            successful = terminal["success"]
            self.trace_lines.append(str(terminal["summary"])[:500])
            break

        snapshot = await _controller_snapshot(session)
        url, title = parse_mcp_snapshot(snapshot)
        if urlparse(url).hostname not in task.policy.allowed_domains:
            raise McpPilotError("final browser state is outside the task allowlist")
        return McpPilotResult(
            done=done,
            successful=successful,
            action_count=action_count,
            final_url=url,
            final_title=title,
            visible_text=snapshot,
            usage=self.usage,
            trace="\n".join(self.trace_lines),
        )

    async def _request(
        self, *, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        request_payload: dict[str, object] = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "parallel_tool_calls": False,
            "reasoning_effort": "none",
        }
        if self.max_completion_tokens is not None:
            request_payload["max_completion_tokens"] = self.max_completion_tokens
        for retry_index in range(3):
            response = await self.client.post(
                f"{OPENROUTER_ENDPOINT}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=request_payload,
                timeout=120,
            )
            if response.status_code == 429 and retry_index < 2:
                delay = _rate_limit_delay(response)
                self._emit(
                    f"provider rate limited; retry {retry_index + 1}/2 after {delay:.1f}s"
                )
                await asyncio.sleep(delay)
                continue
            if response.is_error:
                raise McpPilotError(
                    f"OpenRouter returned HTTP {response.status_code}: {response.text[:1_000]}"
                )
            payload = response.json()
            if not isinstance(payload, dict):
                raise McpPilotError("OpenRouter response is not an object")
            return payload
        raise AssertionError("unreachable rate-limit retry loop")

    def _emit(self, message: str) -> None:
        if self.progress is not None:
            self.progress(message)


def _rate_limit_delay(response: httpx.Response) -> float:
    retry_after = response.headers.get("retry-after")
    if retry_after is not None:
        try:
            return min(max(float(retry_after), 0.1), 10.0)
        except ValueError:
            pass
    match = re.search(r"try again in ([0-9.]+)s", response.text, flags=re.IGNORECASE)
    if match:
        return min(max(float(match.group(1)) + 0.1, 0.1), 10.0)
    return 1.0


def _openrouter_tools(tools: list[Tool]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for tool in tools:
        if tool.name not in ALLOWED_MCP_TOOLS:
            continue
        parameters = tool.inputSchema
        selected.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or tool.name,
                    "parameters": parameters,
                },
            }
        )
    if {item["function"]["name"] for item in selected} != ALLOWED_MCP_TOOLS:
        raise McpPilotError("Playwright MCP tool contract is incomplete")
    return selected


def _task_prompt(task: TaskSpec) -> str:
    return (
        task.instruction.strip()
        + "\n\nCompletion: "
        + task.completion
        + "\nAllowed domains: "
        + ", ".join(task.policy.allowed_domains)
    )


def _assistant_message(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        message = payload["choices"][0]["message"]
    except (IndexError, KeyError, TypeError) as error:
        raise McpPilotError("OpenRouter response lacks an assistant message") from error
    if not isinstance(message, dict):
        raise McpPilotError("OpenRouter assistant message is invalid")
    return message


def _provider_usage(payload: dict[str, Any]) -> tuple[int, int, float | None]:
    try:
        usage = payload["usage"]
        prompt = usage["prompt_tokens"]
        completion = usage["completion_tokens"]
    except (KeyError, TypeError) as error:
        raise McpPilotError("provider response lacks comparable usage") from error
    if not isinstance(prompt, int) or not isinstance(completion, int):
        raise McpPilotError("provider token usage is invalid")
    return prompt, completion, provider_cost_or_luna_estimate(usage)


def _parse_tool_call(call: object) -> tuple[str, dict[str, Any], str]:
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


def _normalize_mcp_tool_arguments(*, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Normalize known model spellings to the Playwright MCP tool contract."""
    target = arguments.get("target")
    normalized = arguments
    if name in ALLOWED_MCP_TOOLS and isinstance(target, str):
        match = re.fullmatch(r"ref=(e[1-9][0-9]*)", target)
        if match:
            normalized = {**normalized, "target": match.group(1)}
    regex = normalized.get("regex")
    if name == "browser_find" and isinstance(regex, str):
        # Playwright MCP accepts JavaScript flags after the closing slash. Models
        # sometimes emit Python's leading (?i), which the driver rejects.
        match = re.fullmatch(r"/\(\?i\)(.*)/([a-z]*)", regex, flags=re.DOTALL)
        if match:
            flags = match.group(2)
            normalized = {
                **normalized,
                "regex": f"/{match.group(1)}/{flags if 'i' in flags else flags + 'i'}",
            }
    return normalized


def _validate_tool_call(*, name: str, arguments: dict[str, Any], task: TaskSpec) -> None:
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


async def _controller_snapshot(session: ClientSession) -> str:
    result = await session.call_tool("browser_snapshot", {"depth": 6, "boxes": False})
    text = _tool_text(result)
    if result.isError:
        raise McpPilotError("controller snapshot failed: " + text[:1_000])
    return text


def _terminal_output(content: object) -> TerminalOutput:
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
    if not isinstance(value["summary"], str):
        raise McpPilotError("terminal summary is invalid")
    return TerminalOutput(done=True, success=value["success"], summary=value["summary"])


def _tool_text(result: object) -> str:
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
