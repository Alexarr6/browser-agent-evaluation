from __future__ import annotations

import contextlib
import json
import shutil
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool

from browser_agent_evaluation.agents.playwright_mcp.runner import PlaywrightMcpPilot
from browser_agent_evaluation.agents.playwright_mcp.tools import (
    ALLOWED_MCP_TOOLS,
    McpPilotError,
    assistant_message,
    controller_snapshot,
    normalize_tool_arguments,
    openrouter_tools,
    parse_mcp_snapshot,
    parse_tool_call,
    provider_usage,
    terminal_output,
    tool_text,
    validate_tool_call,
)
from browser_agent_evaluation.connectors.base import (
    CleanupResult,
    ConnectorSession,
    ConnectorStepResult,
    ObservedPageState,
    SessionRequest,
)
from browser_agent_evaluation.core.models import UsageEvidence
from browser_agent_evaluation.providers.openai import COMMON_MODEL


@dataclass
class PlaywrightMcpSession(ConnectorSession):
    """One persistent Playwright MCP session per workflow run."""

    request: SessionRequest
    api_key: str
    executable: Path
    node_modules: Path
    trial_id: str
    model_id: str = COMMON_MODEL
    max_completion_tokens: int | None = None
    max_total_usd: float | None = None
    max_run_usd: float | None = None
    max_tokens_per_run: int | None = None
    headless: bool = True
    max_model_requests: int = 24
    max_tool_calls: int = 24
    pilot: PlaywrightMcpPilot | None = None
    client_session: ClientSession | None = None
    exit_stack: AsyncExitStack | None = None
    session_state: dict[str, Any] = field(default_factory=dict)
    available_tools: list[Tool] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)
    action_count: int = 0
    usage: UsageEvidence = field(
        default_factory=lambda: UsageEvidence(
            prompt_tokens=None,
            completion_tokens=None,
            request_count=0,
            cost_usd=None,
            unavailable_reason="MCP session did not start",
        )
    )
    last_trace: str = ""

    if TYPE_CHECKING:
        from browser_agent_evaluation.core.models import TaskSpec

    async def open_async(self) -> PlaywrightMcpSession:
        await self._start()
        return self

    async def _start(self) -> None:
        temporary_output = Path("/tmp") / f"{self.trial_id}-mcp"
        temporary_output.mkdir(exist_ok=True)
        self.session_state["temporary_output"] = temporary_output
        params = StdioServerParameters(
            command=_node_executable(),
            args=[
                str(self.node_modules / "@playwright/mcp/cli.js"),
                *( ["--headless"] if self.headless else [] ),
                "--isolated",
                "--block-service-workers",
                "--executable-path",
                str(self.executable),
                "--output-dir",
                str(temporary_output),
                "--allowed-origins",
                _task_origin(self.request),
                "--timeout-action",
                "600000",
                "--timeout-navigation",
                "600000",
                "--codegen",
                "none",
                "--image-responses",
                "omit",
            ],
            env={"PATH": _parent_dir(_node_executable()), "HOME": "/tmp"},
            cwd=self.node_modules,
        )
        exit_stack = AsyncExitStack()
        read, write = await exit_stack.enter_async_context(stdio_client(params))
        client_session = ClientSession(read, write)
        await exit_stack.enter_async_context(client_session)
        await client_session.initialize()
        self.client_session = client_session
        self.exit_stack = exit_stack
        self.available_tools = (await client_session.list_tools()).tools
        allowed = {tool.name for tool in self.available_tools} & ALLOWED_MCP_TOOLS
        if allowed != ALLOWED_MCP_TOOLS:
            raise McpPilotError("Playwright MCP tool contract is incomplete")
        initial = await client_session.call_tool(
            "browser_navigate", {"url": self.request.start_url}
        )
        if initial.isError:
            raise McpPilotError("initial MCP navigation failed: " + tool_text(initial)[:1_000])
        initial_snapshot = await controller_snapshot(client_session)
        url, _ = parse_mcp_snapshot(initial_snapshot)
        if urlparse(url).hostname not in self.request.policy.allowed_domains:
            raise McpPilotError("initial MCP navigation is outside the allowlist")
        self.messages = [
            {
                "role": "system",
                "content": (
                    "You control a browser only through the supplied tools. Use exactly one tool "
                    "per response. A current full-page snapshot is supplied after every action; "
                    "do not request observations. Never use JavaScript, files, downloads, "
                    "credentials, or domains outside the task allowlist. When the task is "
                    "complete, return exactly "
                    '{"done":true,"success":true,"summary":"..."} with no tool call.'
                ),
            },
            {"role": "user", "content": _session_prompt(self.request)},
            {"role": "user", "content": "Initial browser state:\n" + initial_snapshot},
        ]

    async def execute_step(self, request: object) -> ConnectorStepResult:
        del request
        if self.client_session is None:
            raise McpPilotError("MCP session is not open")
        before_usage = self.pilot.usage if self.pilot else self.usage
        last_diagnostic: str | None = None
        for _ in range(self.max_model_requests):
            pilot = self._ensure_pilot()
            pilot.budget.before_request(pilot.trial_id)
            payload = await pilot._request(
                messages=self.messages,
                tools=openrouter_tools(self.available_tools),
            )
            prompt, completion, cost = provider_usage(payload)
            pilot.budget.consume_usage(pilot.trial_id, cost, prompt, completion)
            self.usage = pilot.usage
            self.last_trace = json.dumps(payload, sort_keys=True)[:1_000]
            message = assistant_message(payload)
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                content = message.get("content")
                try:
                    terminal = terminal_output(content)
                except McpPilotError as error:
                    last_diagnostic = str(error)
                    break
                self.messages.append(message)
                self.session_state["terminal"] = terminal
                break
            if len(tool_calls) != 1:
                last_diagnostic = "model must request exactly one MCP tool per turn"
                break
            if self.action_count >= self.max_tool_calls:
                last_diagnostic = "MCP tool call cap reached"
                break
            call = tool_calls[0]
            name, arguments, call_id = parse_tool_call(call)
            arguments = normalize_tool_arguments(name=name, arguments=arguments)
            validate_tool_call(name=name, arguments=arguments, task=self._task())
            result = await self.client_session.call_tool(name, arguments)
            result_text = tool_text(result)
            if result.isError:
                last_diagnostic = f"MCP tool failed: {name} {json.dumps(arguments, sort_keys=True)}"
                self.last_trace = result_text[:1_000]
                break
            snapshot = await controller_snapshot(self.client_session)
            self.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": (result_text + "\nCurrent browser state:\n" + snapshot)[-20_000:],
                }
            )
            self.action_count += 1
        return ConnectorStepResult(
            action_summary=[f"mcp:{self.action_count}"],
            usage=usage_delta(before_usage, self.usage),
            diagnostic=last_diagnostic,
        )

    async def observe(self) -> ObservedPageState:
        if self.client_session is None:
            raise McpPilotError("MCP session is not open")
        snapshot = await controller_snapshot(self.client_session)
        url, title = parse_mcp_snapshot(snapshot)
        return ObservedPageState(
            url=url,
            title=title,
            visible_text=snapshot,
            input_values={},
        )

    async def close(self) -> CleanupResult:
        await self._stop()
        return CleanupResult(verified=True, detail="MCP session closed via MCP stdio shutdown")

    async def _stop(self) -> None:
        if self.client_session is not None:
            try:
                await self.client_session.call_tool("browser_close", {})
            except McpPilotError:
                pass
            except Exception:  # noqa: BLE001
                pass
        if self.exit_stack is not None:
            with contextlib.suppress(
                httpx.RemoteProtocolError, RuntimeError, ValueError, BrokenPipeError
            ):
                await self.exit_stack.aclose()
            self.exit_stack = None
        self.client_session = None
        temporary_output = self.session_state.pop("temporary_output", None)
        if temporary_output is not None:
            shutil.rmtree(temporary_output, ignore_errors=True)

    def _ensure_pilot(self) -> PlaywrightMcpPilot:
        if self.pilot is None:
            from browser_agent_evaluation.core.budget import ModelBudget

            budget = ModelBudget(
                max_total_usd=self.max_total_usd,
                max_trial_usd=self.max_run_usd,
                max_requests_per_trial=self.max_model_requests,
                max_tokens_per_trial=self.max_tokens_per_run,
            )
            budget.start_trial(self.trial_id)
            client = httpx.AsyncClient()
            self.session_state.setdefault("client", client)
            self.pilot = PlaywrightMcpPilot(
                api_key=self.api_key,
                client=client,
                budget=budget,
                trial_id=self.trial_id,
                model=self.model_id,
                max_completion_tokens=self.max_completion_tokens,
                max_model_requests=self.max_model_requests,
                max_tool_calls=self.max_tool_calls,
            )
            self.pilot.messages = self.messages  # type: ignore[attr-defined]
        return self.pilot

    def _task(self) -> TaskSpec:
        from browser_agent_evaluation.core.models import AcceptanceSpec, TaskSpec

        return TaskSpec(
            schema_version=1,
            id=f"{self.trial_id}-session",
            start_url=self.request.start_url,
            instruction="persistent MCP session",
            completion="session finishes when closed",
            policy=self.request.policy,
            max_actions=2**31 - 1,
            timeout_seconds=2**31 - 1,
            acceptance=AcceptanceSpec(page_title=" "),
        )


def _task_origin(request: SessionRequest) -> str:
    parsed = urlparse(request.start_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _session_prompt(request: SessionRequest) -> str:
    domains = ", ".join(request.policy.allowed_domains)
    return (
        "This session opens the browser at "
        + request.start_url
        + " and remains open across all workflow steps. Stay inside the allowed "
        "domains and never download files or use credentials. Allowed domains: " + domains + "."
    )


def _node_executable() -> str:
    from pathlib import Path

    candidates = (
        shutil.which("node"),
        "/usr/bin/node",
        "/usr/local/bin/node",
        "/home/pi/.local/share/pi-node/node-v22.23.2-linux-arm64/bin/node",
    )
    for candidate in candidates:
        if candidate is None:
            continue
        path = Path(candidate)
        if path.is_file():
            return str(path)
    raise RuntimeError("node executable is unavailable; install Node.js for Playwright MCP")


def _parent_dir(executable: str) -> str:
    from pathlib import Path

    return str(Path(executable).parent)


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
