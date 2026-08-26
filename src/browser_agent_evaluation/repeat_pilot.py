from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import shutil
import traceback
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from urllib.parse import urlparse

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from playwright.async_api import async_playwright

from browser_agent_evaluation.assertions import PageState, evaluate_acceptance
from browser_agent_evaluation.browser_use_pilot import (
    VISUAL_PARITY_VIEWPORT,
    BrowserUsePilotError,
    run_browser_use_task,
)
from browser_agent_evaluation.budget import ModelBudget
from browser_agent_evaluation.configuration import load_experiment_configuration
from browser_agent_evaluation.evidence import write_trial_evidence
from browser_agent_evaluation.micro_pilot import _run_reference, _run_restricted, load_task
from browser_agent_evaluation.models import TaskSpec, TrialEvidence, UsageEvidence, now_utc
from browser_agent_evaluation.playwright_mcp_pilot import PlaywrightMcpPilot
from browser_agent_evaluation.provider import COMMON_MODEL
from browser_agent_evaluation.runtime_environment import load_local_runtime_environment

EXPERIMENT_ROOT = Path(__file__).resolve().parents[2]
TASKS_ROOT = EXPERIMENT_ROOT / "tasks"
AI_RUNNERS = ("restricted", "browser_use", "playwright_mcp")
TASK_FILENAMES = (
    "wikipedia-search.yaml",
    "mdn-reference.yaml",
    "selenium-web-form.yaml",
    "selenium-ajax-labels.yaml",
    "selenium-key-events.yaml",
)
EXPERIMENTAL_ENGLISH_TASK_FILENAMES = (
    "marca-real-madrid-open-en.yaml",
    "amazon-cheapest-coffee-beans-en.yaml",
)
TASK_PATHS = tuple(TASKS_ROOT / filename for filename in TASK_FILENAMES)
STANDARD_ENGLISH_TASK_PATHS = tuple(
    TASKS_ROOT / "en" / filename.replace(".yaml", "-en.yaml") for filename in TASK_FILENAMES
)
EXPERIMENTAL_ENGLISH_TASK_PATHS = tuple(
    TASKS_ROOT / "experimental" / filename for filename in EXPERIMENTAL_ENGLISH_TASK_FILENAMES
)
ENGLISH_TASK_PATHS = STANDARD_ENGLISH_TASK_PATHS + EXPERIMENTAL_ENGLISH_TASK_PATHS
CHROMIUM_151 = Path.home() / ".cache/ms-playwright/chromium-1234/chrome-linux/chrome"
CHROMIUM_140 = Path.home() / ".cache/ms-playwright/chromium-1187/chrome-linux/chrome"
MCP_ACTION_TIMEOUT_SECONDS = 60
MCP_NAVIGATION_TIMEOUT_SECONDS = 90


@dataclass(frozen=True)
class RoundTask:
    task: TaskSpec
    runners: tuple[str, ...]


def build_round_plan(
    tasks: Iterable[TaskSpec], *, seed: int, runners: tuple[str, ...] = AI_RUNNERS
) -> list[RoundTask]:
    """Return a deterministic randomized task and selected AI-runner order for one round."""
    if not runners or any(runner not in AI_RUNNERS for runner in runners):
        raise ValueError("round plan requires one or more supported AI runners")
    generator = random.Random(seed)
    shuffled_tasks = list(tasks)
    generator.shuffle(shuffled_tasks)
    plan: list[RoundTask] = []
    for task in shuffled_tasks:
        shuffled_runners = list(runners)
        generator.shuffle(shuffled_runners)
        plan.append(RoundTask(task=task, runners=tuple(shuffled_runners)))
    return plan


async def run_round(
    *,
    tasks: list[TaskSpec],
    output_dir: Path,
    api_key: str,
    seed: int,
    round_index: int,
    max_total_usd: float,
    max_trial_usd: float,
    max_requests_per_trial: int,
    max_tokens_per_trial: int | None,
    runners: tuple[str, ...] = AI_RUNNERS,
    browser_use_model: str = COMMON_MODEL,
    headless: bool = True,
    rendering_profile: str = "strict",
) -> list[Path]:
    """Run references and all AI arms once per task with one shared round budget."""
    if rendering_profile not in {"strict", "visual-parity"}:
        raise ValueError("rendering_profile must be strict or visual-parity")
    visual_parity = rendering_profile == "visual-parity"
    artifacts: list[Path] = []
    budget = ModelBudget(
        max_total_usd=max_total_usd,
        max_trial_usd=max_trial_usd,
        max_requests_per_trial=max_requests_per_trial,
        max_tokens_per_trial=max_tokens_per_trial,
    )
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=headless, executable_path=str(CHROMIUM_151)
        )
        try:
            for planned in build_round_plan(tasks, seed=seed, runners=runners):
                reference_progress = _progress_reporter(
                    round_index=round_index,
                    runner="playwright_reference",
                    task_id=planned.task.id,
                )
                reference_progress("started")
                reference, reference_passed = await _run_reference(
                    browser,
                    planned.task,
                    output_dir,
                    restrict_network=not visual_parity,
                    viewport=(VISUAL_PARITY_VIEWPORT if visual_parity else None),
                )
                artifacts.append(reference)
                _report_artifact(reference_progress, reference)
                if not reference_passed:
                    continue
                for runner in planned.runners:
                    trial_id = f"{runner}-r{round_index}-{uuid.uuid4().hex[:12]}"
                    progress = _progress_reporter(
                        round_index=round_index, runner=runner, task_id=planned.task.id
                    )
                    progress("started")
                    if runner == "restricted":
                        artifact = await asyncio.wait_for(
                            _run_restricted(
                                browser,
                                planned.task,
                                output_dir,
                                api_key,
                                budget=budget,
                                trial_id=trial_id,
                                restrict_network=not visual_parity,
                                viewport=(VISUAL_PARITY_VIEWPORT if visual_parity else None),
                                progress=progress,
                            ),
                            timeout=planned.task.timeout_seconds,
                        )
                    elif runner == "browser_use":
                        artifact = await _run_browser_use_trial(
                            task=planned.task,
                            output_dir=output_dir,
                            api_key=api_key,
                            budget=budget,
                            trial_id=trial_id,
                            model_id=browser_use_model,
                            headless=headless,
                            visual_parity=visual_parity,
                        )
                    else:
                        artifact = await _run_mcp_trial(
                            task=planned.task,
                            output_dir=output_dir,
                            api_key=api_key,
                            budget=budget,
                            trial_id=trial_id,
                            headless=headless,
                            visual_parity=visual_parity,
                            progress=progress,
                        )
                    artifacts.append(artifact)
                    _report_artifact(progress, artifact)
        finally:
            await browser.close()
    return artifacts


async def _run_browser_use_trial(
    *,
    task: TaskSpec,
    output_dir: Path,
    api_key: str,
    budget: ModelBudget,
    trial_id: str,
    model_id: str,
    headless: bool,
    visual_parity: bool = False,
) -> Path:
    started = now_utc()
    budget.start_trial(trial_id)
    try:
        result = await asyncio.wait_for(
            run_browser_use_task(
                task=task,
                api_key=api_key,
                chromium_executable=CHROMIUM_140,
                max_steps=task.max_actions,
                budget=budget,
                trial_id=trial_id,
                model=model_id,
                headless=headless,
                visual_parity=visual_parity,
            ),
            timeout=task.timeout_seconds,
        )
    except BrowserUsePilotError as error:
        ended = now_utc()
        evidence = TrialEvidence(
            trial_id=trial_id,
            task_id=task.id,
            runner="browser_use",
            model_id=model_id,
            started_at=started,
            ended_at=ended,
            duration_ms=_duration_ms(started, ended),
            outcome="failed" if error.cleanup_verified else "invalidated",
            action_count=0,
            retry_count=0,
            cleanup_verified=error.cleanup_verified,
            assertion_results={},
            invalidation_reason=(None if error.cleanup_verified else str(error)[:500]),
            policy_events=[type(error).__name__],
            observation_mode="framework_owned",
            usage=error.usage,
        )
        return write_trial_evidence(
            evidence,
            output_dir=output_dir,
            raw_trace=error.trace or str(error),
            markers=[api_key],
            forbidden_paths=[str(Path.home())],
            max_trace_bytes=8_000,
        )
    ended = now_utc()
    passed = result.done and result.successful is True and all(result.assertion_results.values())
    evidence = TrialEvidence(
        trial_id=trial_id,
        task_id=task.id,
        runner="browser_use",
        model_id=model_id,
        started_at=started,
        ended_at=ended,
        duration_ms=_duration_ms(started, ended),
        outcome="passed" if passed else "failed",
        action_count=result.action_count,
        retry_count=0,
        cleanup_verified=True,
        assertion_results=result.assertion_results,
        policy_events=[] if passed else ["framework_or_acceptance_failed"],
        observation_mode="framework_owned",
        usage=result.usage,
    )
    return write_trial_evidence(
        evidence,
        output_dir=output_dir,
        raw_trace=result.last_model_output,
        markers=[api_key],
        forbidden_paths=[str(Path.home())],
        max_trace_bytes=8_000,
    )


async def _run_mcp_trial(
    *,
    task: TaskSpec,
    output_dir: Path,
    api_key: str,
    budget: ModelBudget,
    trial_id: str,
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
            str(EXPERIMENT_ROOT / "node_modules/@playwright/mcp/cli.js"),
            *(["--headless"] if headless else []),
            "--isolated",
            "--block-service-workers",
            "--executable-path",
            str(CHROMIUM_151),
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
            *( ["--viewport-size", "1920x1080"] if visual_parity else [] ),
            *( [] if visual_parity else ["--allowed-origins", _task_origins(task)] ),
        ],
        env=child_env,
        cwd=EXPERIMENT_ROOT,
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


def _task_origins(task: TaskSpec) -> str:
    parsed = urlparse(task.start_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"task start URL lacks an origin: {task.id}")
    return ";".join(f"{parsed.scheme}://{domain}" for domain in task.policy.allowed_domains)


def _duration_ms(started: object, ended: object) -> int:
    return int((ended - started).total_seconds() * 1_000)  # type: ignore[operator]


def _progress_reporter(*, round_index: int, runner: str, task_id: str) -> Callable[[str], None]:
    started = monotonic()
    prefix = f"[round {round_index} | {runner} | {task_id}]"

    def report(message: str) -> None:
        print(f"{prefix} +{monotonic() - started:.1f}s {message}", flush=True)

    return report


def _report_artifact(progress: Callable[[str], None], artifact: Path) -> None:
    evidence = json.loads(artifact.read_text(encoding="utf-8"))
    progress(
        "finished "
        f"outcome={evidence['outcome']} actions={evidence['action_count']} "
        f"duration={evidence['duration_ms'] / 1_000:.1f}s evidence={artifact.name}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run configuration-driven randomized browser-evaluation rounds"
    )
    parser.add_argument("--config", type=Path, default=EXPERIMENT_ROOT / "experiment.yaml")
    parser.add_argument("--round", type=int, default=1, help="first round index")
    parser.add_argument("--repetitions", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--task-language", choices=("es", "en"), default=None)
    parser.add_argument("--max-total-usd", type=float, default=None)
    parser.add_argument("--max-trial-usd", type=float, default=None)
    parser.add_argument("--max-requests-per-trial", type=int, default=None)
    parser.add_argument("--max-tokens-per-trial", type=int, default=None)
    parser.add_argument("--runners", nargs="+", choices=AI_RUNNERS, default=None)
    parser.add_argument("--browser-use-model", default=None)
    parser.add_argument(
        "--rendering-profile",
        choices=("strict", "visual-parity"),
        default="strict",
        help="strict blocks cross-origin assets; visual-parity loads them and fixes the viewport",
    )
    parser.add_argument(
        "--task-path",
        nargs="+",
        type=Path,
        help="explicit task YAML path(s), overriding the configured English task matrix",
    )
    parser.add_argument("--output-dir", type=Path)

    args = parser.parse_args()
    load_local_runtime_environment(EXPERIMENT_ROOT / ".env")
    configuration = load_experiment_configuration(args.config)
    api_key = os.environ.get(configuration.provider.api_key_env, "")
    if not api_key:
        raise SystemExit(
            f"{configuration.provider.api_key_env} is required for the approved repeated pilot"
        )
    if args.round < 1:
        raise SystemExit("--round must be positive")
    repetitions = args.repetitions or configuration.execution.repetitions
    if repetitions < 1:
        raise SystemExit("--repetitions must be positive")
    task_language = args.task_language or configuration.execution.task_language
    runners = tuple(
        args.runners
        or [runner for runner in configuration.enabled_runner_ids if runner in AI_RUNNERS]
    )
    if not runners:
        raise SystemExit("configuration enables no AI runner")
    max_total_usd = (
        args.max_total_usd if args.max_total_usd is not None else configuration.budget.max_total_usd
    )
    max_trial_usd = (
        args.max_trial_usd if args.max_trial_usd is not None else configuration.budget.max_run_usd
    )
    if max_total_usd is None or max_trial_usd is None:
        raise SystemExit("set --max-total-usd and --max-trial-usd for the repeated pilot")
    output_dir = args.output_dir or EXPERIMENT_ROOT / "runs/repeated" / task_language
    all_artifacts: list[Path] = []
    for round_index in range(args.round, args.round + repetitions):
        all_artifacts.extend(
            asyncio.run(
                run_round(
                    tasks=[
                        load_task(path)
                        for path in (
                            args.task_path
                            if args.task_path is not None
                            else (ENGLISH_TASK_PATHS if task_language == "en" else TASK_PATHS)
                        )
                    ],
                    output_dir=output_dir,
                    api_key=api_key,
                    seed=(args.seed if args.seed is not None else configuration.execution.seed)
                    + round_index
                    - 1,
                    round_index=round_index,
                    max_total_usd=max_total_usd,
                    max_trial_usd=max_trial_usd,
                    max_requests_per_trial=(
                        args.max_requests_per_trial
                        if args.max_requests_per_trial is not None
                        else configuration.execution.max_requests_per_run
                    ),
                    max_tokens_per_trial=(
                        args.max_tokens_per_trial
                        if args.max_tokens_per_trial is not None
                        else configuration.budget.max_tokens_per_run
                    ),
                    runners=runners,
                    browser_use_model=(
                        args.browser_use_model or configuration.runners.browser_use.model
                    ),
                    headless=configuration.browser.headless,
                    rendering_profile=args.rendering_profile,
                )
            )
        )
    print("\n".join(str(path) for path in all_artifacts))


if __name__ == "__main__":
    main()
