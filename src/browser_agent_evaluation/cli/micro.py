from __future__ import annotations

import asyncio
import os
from collections.abc import Sequence
from pathlib import Path

from playwright.async_api import async_playwright

from browser_agent_evaluation.browser.binaries import configured_executable
from browser_agent_evaluation.browser.environment import load_local_runtime_environment
from browser_agent_evaluation.configuration.loader import load_experiment_configuration
from browser_agent_evaluation.configuration.paths import PROJECT_ROOT
from browser_agent_evaluation.core.models import TaskSpec
from browser_agent_evaluation.evaluation.reference_trial import run_reference_trial
from browser_agent_evaluation.evaluation.restricted_trial import run_restricted_trial
from browser_agent_evaluation.evaluation.tasks import load_task


async def run_micro_pilot(
    *,
    task: TaskSpec,
    output_dir: Path,
    api_key: str,
    chromium_executable: Path,
    model: str,
    provider_endpoint: str,
) -> list[Path]:
    artifacts: list[Path] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True, executable_path=str(chromium_executable)
        )
        try:
            reference_artifact, reference_passed = await run_reference_trial(
                browser, task, output_dir
            )
            artifacts.append(reference_artifact)
            if reference_passed:
                artifacts.append(
                    await run_restricted_trial(
                        browser,
                        task,
                        output_dir,
                        api_key,
                        model=model,
                        provider_endpoint=provider_endpoint,
                    )
                )
        finally:
            await browser.close()
    return artifacts


def main(argv: Sequence[str] | None = None) -> None:
    if argv:
        raise SystemExit("browser-eval micro does not accept command-line arguments")
    load_local_runtime_environment(PROJECT_ROOT / ".env")
    configuration = load_experiment_configuration(PROJECT_ROOT / "experiment.yaml")
    api_key = os.environ.get(configuration.provider.api_key_env, "")
    if not api_key:
        raise SystemExit(f"{configuration.provider.api_key_env} is required for the micro-pilot")
    task_path = Path(
        os.environ.get(
            "BROWSER_EVAL_TASK_PATH",
            str(PROJECT_ROOT / "tasks/wikipedia-search.yaml"),
        )
    )
    artifacts = asyncio.run(
        run_micro_pilot(
            task=load_task(task_path),
            output_dir=PROJECT_ROOT / "runs/micro-pilot",
            api_key=api_key,
            chromium_executable=configured_executable(configuration.browser.executable_path_env),
            model=configuration.runners.restricted.model,
            provider_endpoint=configuration.provider.endpoint,
        )
    )
    print("\n".join(str(path) for path in artifacts))
