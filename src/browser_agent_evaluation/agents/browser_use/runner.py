from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from browser_agent_evaluation.agents.browser_use.model import BrowserUseChatModel
from browser_agent_evaluation.agents.browser_use.usage import ChatCompletionsUsageCapture
from browser_agent_evaluation.browser.environment import BROWSER_USE_PRIVACY_OVERRIDES
from browser_agent_evaluation.core.assertions import PageState, evaluate_acceptance
from browser_agent_evaluation.core.budget import ModelBudget
from browser_agent_evaluation.core.models import TaskSpec, UsageEvidence, render_runner_instruction
from browser_agent_evaluation.providers.chat_completions import (
    DEFAULT_MODEL,
    require_comparable_usage,
)


class BrowserUsePilotError(RuntimeError):
    """Reports browser-use failure with the evidence available before cleanup."""

    def __init__(self, message: str, *, usage: UsageEvidence, trace: str, cleanup_verified: bool):
        super().__init__(message)
        self.usage = usage
        self.trace = trace
        self.cleanup_verified = cleanup_verified


class ExternalBrowserLaunchBlocked(BrowserUsePilotError):
    """Raised when browser-use asks the host to open a non-isolated browser."""


VISUAL_PARITY_VIEWPORT = {"width": 1920, "height": 1080}


@contextmanager
def _block_external_browser_launch() -> Iterator[Path]:
    """Prevent xdg-open from escaping the approved headless browser process."""
    with tempfile.TemporaryDirectory(prefix="browser-eval-no-xdg-") as directory:
        root = Path(directory)
        log = root / "blocked-xdg-open.log"
        launcher = root / "xdg-open"
        launcher.write_text(
            '#!/bin/sh\nprintf \'%s\\n\' "$*" >> "$BROWSER_EVAL_BLOCKED_OPEN_LOG"\nexit 126\n',
            encoding="utf-8",
        )
        launcher.chmod(0o700)
        original_path = os.environ.get("PATH", "")
        original_log = os.environ.get("BROWSER_EVAL_BLOCKED_OPEN_LOG")
        os.environ["PATH"] = f"{root}{os.pathsep}{original_path}"
        os.environ["BROWSER_EVAL_BLOCKED_OPEN_LOG"] = str(log)
        try:
            yield log
        finally:
            os.environ["PATH"] = original_path
            if original_log is None:
                os.environ.pop("BROWSER_EVAL_BLOCKED_OPEN_LOG", None)
            else:
                os.environ["BROWSER_EVAL_BLOCKED_OPEN_LOG"] = original_log


@dataclass(frozen=True)
class BrowserUsePilotResult:
    usage: UsageEvidence
    done: bool
    successful: bool | None
    action_count: int
    final_url: str | None
    assertion_results: dict[str, bool]
    last_model_output: str


async def run_browser_use_task(
    *,
    task: TaskSpec,
    api_key: str,
    chromium_executable: Path,
    max_steps: int,
    budget: ModelBudget,
    trial_id: str,
    provider_endpoint: str,
    model: str = DEFAULT_MODEL,
    headless: bool = True,
    visual_parity: bool = False,
) -> BrowserUsePilotResult:
    """Run one approved local browser-use task with provider-reported usage."""
    if not api_key:
        raise ValueError("provider API key is required")
    if max_steps < 1 or max_steps > task.max_actions:
        raise ValueError("browser-use step cap must fit task action cap")
    os.environ.update(BROWSER_USE_PRIVACY_OVERRIDES)
    from browser_use import Agent, Browser, Tools

    capture = ChatCompletionsUsageCapture(httpx.AsyncHTTPTransport())
    llm: BrowserUseChatModel | None = None
    cleanup_verified = False
    try:
        with _block_external_browser_launch() as blocked_launch_log:
            async with httpx.AsyncClient(transport=capture) as client:
                llm = BrowserUseChatModel(
                    api_key=api_key,
                    http_client=client,
                    budget=budget,
                    trial_id=trial_id,
                    model=model,
                    endpoint=provider_endpoint,
                )
                browser = Browser(
                    executable_path=chromium_executable,
                    headless=headless,
                    viewport=(VISUAL_PARITY_VIEWPORT if visual_parity else None),
                    window_size=(VISUAL_PARITY_VIEWPORT if visual_parity else None),
                    allowed_domains=task.policy.allowed_domains,
                    keep_alive=True,
                    accept_downloads=False,
                    enable_default_extensions=False,
                )
                try:
                    agent: Any = Agent(
                        task=render_runner_instruction(task),
                        llm=llm,
                        browser=browser,
                        directly_open_url=False,
                        tools=Tools(
                            exclude_actions=[
                                "evaluate",
                                "upload_file",
                                "read_file",
                                "write_file",
                                "replace_file",
                                "save_as_pdf",
                            ]
                        ),
                        use_vision=False,
                        use_thinking=False,
                        enable_planning=False,
                        max_actions_per_step=1,
                        max_failures=1,
                        final_response_after_failure=False,
                        use_judge=False,
                        calculate_cost=False,
                        enable_signal_handler=False,
                    )
                    await browser.start()
                    await browser.navigate_to(task.start_url)
                    history = await agent.run(max_steps=max_steps)
                    state = await browser.get_browser_state_summary(include_screenshot=False)
                finally:
                    await browser.kill()
                    cleanup_verified = True
            if blocked_launch_log.exists() and blocked_launch_log.read_text(encoding="utf-8"):
                raise ExternalBrowserLaunchBlocked(
                    "browser-use attempted external browser launch",
                    usage=capture.usage,
                    trace=llm.evidence_trace,
                    cleanup_verified=cleanup_verified,
                )
        usage = capture.usage
        require_comparable_usage(usage)
        urls = history.urls()
        assertions = evaluate_acceptance(
            task.acceptance,
            PageState(
                url=state.url,
                title=state.title,
                visible_text=state.dom_state.llm_representation(),
                input_values={},
            ),
        )
        return BrowserUsePilotResult(
            usage=usage,
            done=history.is_done(),
            successful=history.is_successful(),
            action_count=len(history.model_actions()),
            final_url=urls[-1] if urls else None,
            assertion_results=assertions,
            last_model_output=llm.evidence_trace,
        )
    except BrowserUsePilotError:
        raise
    except Exception as error:
        raise BrowserUsePilotError(
            str(error),
            usage=capture.usage,
            trace=llm.evidence_trace if llm else "",
            cleanup_verified=cleanup_verified,
        ) from error
