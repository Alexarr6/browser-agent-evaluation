from __future__ import annotations

import asyncio
import json
import random
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from time import monotonic

from playwright.async_api import async_playwright

from browser_agent_evaluation.agents.browser_use.runner import (
    VISUAL_PARITY_VIEWPORT,
)
from browser_agent_evaluation.configuration.paths import TASKS_ROOT
from browser_agent_evaluation.core.budget import ModelBudget
from browser_agent_evaluation.core.models import TaskSpec
from browser_agent_evaluation.evaluation.browser_use_trial import run_browser_use_trial
from browser_agent_evaluation.evaluation.playwright_mcp_trial import run_playwright_mcp_trial
from browser_agent_evaluation.evaluation.reference_trial import run_reference_trial
from browser_agent_evaluation.evaluation.restricted_trial import run_restricted_trial
from browser_agent_evaluation.providers.chat_completions import DEFAULT_MODEL

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
    reference_chromium: Path,
    browser_use_chromium: Path,
    runners: tuple[str, ...] = AI_RUNNERS,
    model: str = DEFAULT_MODEL,
    provider_endpoint: str,
    headless: bool = True,
    rendering_profile: str = "strict",
    skip_ai_on_reference_failure: bool = False,
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
            headless=headless, executable_path=str(reference_chromium)
        )
        try:
            for planned in build_round_plan(tasks, seed=seed, runners=runners):
                reference_progress = _progress_reporter(
                    round_index=round_index,
                    runner="playwright_reference",
                    task_id=planned.task.id,
                )
                reference_progress("started")
                reference, reference_passed = await run_reference_trial(
                    browser,
                    planned.task,
                    output_dir,
                    restrict_network=not visual_parity,
                    viewport=(VISUAL_PARITY_VIEWPORT if visual_parity else None),
                )
                artifacts.append(reference)
                _report_artifact(reference_progress, reference)
                if not reference_passed and skip_ai_on_reference_failure:
                    continue
                for runner in planned.runners:
                    trial_id = f"{runner}-r{round_index}-{uuid.uuid4().hex[:12]}"
                    progress = _progress_reporter(
                        round_index=round_index, runner=runner, task_id=planned.task.id
                    )
                    progress("started")
                    if runner == "restricted":
                        artifact = await asyncio.wait_for(
                            run_restricted_trial(
                                browser,
                                planned.task,
                                output_dir,
                                api_key,
                                budget=budget,
                                trial_id=trial_id,
                                restrict_network=not visual_parity,
                                viewport=(VISUAL_PARITY_VIEWPORT if visual_parity else None),
                                progress=progress,
                                model=model,
                                provider_endpoint=provider_endpoint,
                            ),
                            timeout=planned.task.timeout_seconds,
                        )
                    elif runner == "browser_use":
                        artifact = await run_browser_use_trial(
                            task=planned.task,
                            output_dir=output_dir,
                            api_key=api_key,
                            budget=budget,
                            trial_id=trial_id,
                            model_id=model,
                            provider_endpoint=provider_endpoint,
                            chromium_executable=browser_use_chromium,
                            headless=headless,
                            visual_parity=visual_parity,
                        )
                    else:
                        artifact = await run_playwright_mcp_trial(
                            task=planned.task,
                            output_dir=output_dir,
                            api_key=api_key,
                            budget=budget,
                            trial_id=trial_id,
                            chromium_executable=reference_chromium,
                            model_id=model,
                            provider_endpoint=provider_endpoint,
                            headless=headless,
                            visual_parity=visual_parity,
                            progress=progress,
                        )
                    artifacts.append(artifact)
                    _report_artifact(progress, artifact)
        finally:
            await browser.close()
    return artifacts


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
