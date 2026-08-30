from __future__ import annotations

import asyncio
import os
import shutil
import traceback
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from browser_agent_evaluation.agents.playwright_mcp.runner import PlaywrightMcpPilot
from browser_agent_evaluation.browser.binaries import (
    MCP_ACTION_TIMEOUT_SECONDS,
    MCP_NAVIGATION_TIMEOUT_SECONDS,
)
from browser_agent_evaluation.configuration.paths import NODE_MODULES_ROOT, PROJECT_ROOT
from browser_agent_evaluation.core.assertions import PageState, evaluate_acceptance
from browser_agent_evaluation.core.budget import ModelBudget
from browser_agent_evaluation.core.models import TaskSpec, TrialEvidence, UsageEvidence, now_utc
from browser_agent_evaluation.reporting.evidence import write_trial_evidence


async def run_playwright_mcp_trial(
    *,
    task: TaskSpec,
    output_dir: Path,
    api_key: str,
    budget: ModelBudget,
    trial_id: str,
    chromium_executable: Path,
    model_id: str,
    provider_endpoint: str,
    headless: bool,
    visual_parity: bool = False,
    progress: Callable[[str], None] | None = None,
) -> Path:
    started = now_utc()
    budget.start_trial(trial_id)
    temporary_output = Path("/tmp") / trial_id
    temporary_output.mkdir()
    child_env = {
        "PATH": os.environ["PATH"],
        "HOME": os.environ["HOME"],
        "PYTHON_DOTENV_DISABLED": "1",
    }
    if not headless:
        display = os.environ.get("DISPLAY")
        if not display:
            raise RuntimeError("headed Playwright MCP requires DISPLAY")
        child_env["DISPLAY"] = display
        if xauthority := os.environ.get("XAUTHORITY"):
            child_env["XAUTHORITY"] = xauthority
    params = StdioServerParameters(
        command="node",
        args=[
            str(NODE_MODULES_ROOT / "@playwright/mcp/cli.js"),
            *(["--headless"] if headless else []),
            "--isolated",
            "--block-service-workers",
            "--executable-path",
            str(chromium_executable),
            "--output-dir",
            str(temporary_output),
            "--timeout-action",
            str(min(task.timeout_seconds, MCP_ACTION_TIMEOUT_SECONDS) * 1_000),
            "--timeout-navigation",
            str(min(task.timeout_seconds, MCP_NAVIGATION_TIMEOUT_SECONDS) * 1_000),
            "--codegen",
            "none",
            "--image-responses",
            "omit",
            *(["--viewport-size", "1920x1080"] if visual_parity else []),
            *([] if visual_parity else ["--allowed-origins", task_origins(task)]),
        ],
        env=child_env,
        cwd=PROJECT_ROOT,
    )
    pilot: PlaywrightMcpPilot | None = None
    result = None
    failure: Exception | None = None
    cleanup_verified = False
    try:
        async with (
            httpx.AsyncClient() as client,
            stdio_client(params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            pilot = PlaywrightMcpPilot(
                api_key=api_key,
                client=client,
                budget=budget,
                trial_id=trial_id,
                model=model_id,
                endpoint=provider_endpoint,
                max_model_requests=budget.max_requests_per_trial,
                max_tool_calls=task.max_actions,
                progress=progress,
            )
            try:
                result = await asyncio.wait_for(
                    pilot.run(
                        task=task,
                        session=session,
                        available_tools=(await session.list_tools()).tools,
                    ),
                    timeout=task.timeout_seconds,
                )
            finally:
                close_result = await session.call_tool("browser_close", {})
                cleanup_verified = not close_result.isError
    except Exception as error:
        failure = error
    finally:
        shutil.rmtree(temporary_output, ignore_errors=True)
    ended = now_utc()
    if failure is not None or result is None or pilot is None:
        usage = (
            pilot.usage
            if pilot is not None
            else UsageEvidence(
                prompt_tokens=None,
                completion_tokens=None,
                request_count=0,
                cost_usd=None,
                unavailable_reason="MCP initialization failed before provider usage capture",
            )
        )
        evidence = TrialEvidence(
            trial_id=trial_id,
            task_id=task.id,
            runner="playwright_mcp",
            started_at=started,
            ended_at=ended,
            duration_ms=_duration_ms(started, ended),
            outcome="failed" if cleanup_verified else "invalidated",
            action_count=pilot.action_count if pilot else 0,
            retry_count=0,
            cleanup_verified=cleanup_verified,
            assertion_results={},
            invalidation_reason=(None if cleanup_verified else str(failure)[:500]),
            policy_events=[type(failure).__name__ if failure else "McpPilotError"],
            observation_mode="mcp_accessibility",
            usage=usage,
        )
        trace = "\n".join(pilot.trace_lines) if pilot else ""
        return write_trial_evidence(
            evidence,
            output_dir=output_dir,
            raw_trace=(trace + "\n" + "".join(traceback.format_exception(failure))).strip(),
            markers=[api_key],
            forbidden_paths=[str(Path.home())],
            max_trace_bytes=8_000,
        )
    assertions = evaluate_acceptance(
        task.acceptance,
        PageState(
            url=result.final_url,
            title=result.final_title,
            visible_text=result.visible_text,
            input_values={},
        ),
    )
    passed = result.done and result.successful and all(assertions.values())
    evidence = TrialEvidence(
        trial_id=trial_id,
        task_id=task.id,
        runner="playwright_mcp",
        started_at=started,
        ended_at=ended,
        duration_ms=_duration_ms(started, ended),
        outcome="passed" if passed else "failed",
        action_count=result.action_count,
        retry_count=0,
        cleanup_verified=True,
        assertion_results=assertions,
        policy_events=[] if passed else ["framework_or_acceptance_failed"],
        observation_mode="mcp_accessibility",
        usage=result.usage,
    )
    return write_trial_evidence(
        evidence,
        output_dir=output_dir,
        raw_trace=result.trace,
        markers=[api_key],
        forbidden_paths=[str(Path.home())],
        max_trace_bytes=8_000,
    )


def task_origins(task: TaskSpec) -> str:
    parsed = urlparse(task.start_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"task start URL lacks an origin: {task.id}")
    return ";".join(f"{parsed.scheme}://{domain}" for domain in task.policy.allowed_domains)


def _duration_ms(started: object, ended: object) -> int:
    return int((ended - started).total_seconds() * 1_000)  # type: ignore[operator]
