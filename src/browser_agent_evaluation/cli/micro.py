from __future__ import annotations

import asyncio
import os
from collections.abc import Sequence
from pathlib import Path

from playwright.async_api import async_playwright

from browser_agent_evaluation.configuration.paths import PROJECT_ROOT
from browser_agent_evaluation.core.models import TaskSpec
from browser_agent_evaluation.evaluation.reference_trial import run_reference_trial
from browser_agent_evaluation.evaluation.restricted_trial import run_restricted_trial
from browser_agent_evaluation.evaluation.tasks import load_task


async def run_micro_pilot(*, task: TaskSpec, output_dir: Path, api_key: str) -> list[Path]:
    artifacts: list[Path] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            reference_artifact, reference_passed = await run_reference_trial(
                browser, task, output_dir
            )
            artifacts.append(reference_artifact)
            if reference_passed:
                artifacts.append(await run_restricted_trial(browser, task, output_dir, api_key))
        finally:
            await browser.close()
    return artifacts


def main(argv: Sequence[str] | None = None) -> None:
    if argv:
        raise SystemExit("browser-eval micro does not accept command-line arguments")
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is required for the approved micro-pilot")
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
        )
    )
    print("\n".join(str(path) for path in artifacts))
