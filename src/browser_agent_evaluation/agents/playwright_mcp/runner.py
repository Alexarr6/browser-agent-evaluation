from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx
from mcp import ClientSession
from mcp.types import Tool

from browser_agent_evaluation.agents.playwright_mcp.tools import (
    McpPilotError,
    assistant_message,
    controller_snapshot,
    normalize_tool_arguments,
    openrouter_tools,
    parse_mcp_snapshot,
    parse_tool_call,
    provider_usage,
    task_prompt,
    terminal_output,
    tool_text,
    validate_tool_call,
)
from browser_agent_evaluation.core.budget import ModelBudget
from browser_agent_evaluation.core.models import TaskSpec, UsageEvidence
from browser_agent_evaluation.providers.openai import COMMON_MODEL, OPENROUTER_ENDPOINT


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
        tools = openrouter_tools(available_tools)
        initial = await session.call_tool("browser_navigate", {"url": task.start_url})
        if initial.isError:
            raise McpPilotError("initial MCP navigation failed: " + tool_text(initial)[:1_000])
        initial_snapshot = await controller_snapshot(session)
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
            {"role": "user", "content": task_prompt(task)},
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
            prompt, completion, cost = provider_usage(payload)
            self.budget.consume_usage(self.trial_id, cost, prompt, completion)
            self.prompt_tokens += prompt
            self.completion_tokens += completion
            self.cost_usd = None if cost is None or self.cost_usd is None else self.cost_usd + cost
            message = assistant_message(payload)
            tool_calls = message.get("tool_calls") or []
            if tool_calls:
                if not isinstance(tool_calls, list) or len(tool_calls) != 1:
                    raise McpPilotError("model must request exactly one MCP tool per turn")
                if action_count >= self.max_tool_calls:
                    raise McpPilotError("MCP tool call cap reached")
                call = tool_calls[0]
                name, arguments, call_id = parse_tool_call(call)
                arguments = normalize_tool_arguments(name=name, arguments=arguments)
                validate_tool_call(name=name, arguments=arguments, task=task)
                messages.append(message)
                self._emit(f"tool {action_count + 1}/{self.max_tool_calls}: {name}")
                result = await session.call_tool(name, arguments)
                result_text = tool_text(result)
                if result.isError:
                    action_count += 1
                    self.action_count = action_count
                    tool_recoveries += 1
                    self.trace_lines.append(f"{name} failed: {result_text[:500]}")
                    if tool_recoveries > 2:
                        raise McpPilotError(
                            f"MCP tool recovery exhausted after {name}: {result_text[:1_000]}"
                        )
                    snapshot = await controller_snapshot(session)
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
                snapshot = await controller_snapshot(session)
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
            terminal = terminal_output(content)
            done = terminal["done"]
            successful = terminal["success"]
            self.trace_lines.append(str(terminal["summary"])[:500])
            break

        snapshot = await controller_snapshot(session)
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
