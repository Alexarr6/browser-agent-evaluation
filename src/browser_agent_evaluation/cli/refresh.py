"""Selective reruns preserve original evidence until the replacement matrix is complete."""

from __future__ import annotations

import argparse
import asyncio
import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path

from playwright.async_api import async_playwright

from browser_agent_evaluation.browser.binaries import configured_executable
from browser_agent_evaluation.browser.environment import load_local_runtime_environment
from browser_agent_evaluation.configuration.loader import load_experiment_configuration
from browser_agent_evaluation.configuration.paths import PROJECT_ROOT
from browser_agent_evaluation.core.models import now_utc
from browser_agent_evaluation.evaluation.reference_trial import run_reference_trial
from browser_agent_evaluation.evaluation.tasks import load_task
from browser_agent_evaluation.reporting.manifest import write_evaluation_manifest
from browser_agent_evaluation.reporting.repeated import load_repeated_evidence


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Rerun selected task slots, preserving backups")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--task-path", type=Path, nargs="+", required=True)
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "experiment.yaml")
    parser.add_argument("--references-only", action="store_true")
    args = parser.parse_args(argv)
    original = load_repeated_evidence(args.manifest)
    manifest = original.manifest
    selected = {load_task(path).id for path in args.task_path}
    if not selected <= {task.id for task in manifest.tasks}:
        raise SystemExit("Selected task IDs must already exist in the target manifest")
    if len(selected) != len(args.task_path):
        raise SystemExit("Duplicate task paths")
    load_local_runtime_environment(PROJECT_ROOT / ".env")
    config = load_experiment_configuration(args.config)
    if config.provider.endpoint != manifest.provider_endpoint:
        raise SystemExit("Provider endpoint differs from the original manifest")
    if manifest.round_indices != list(
        range(manifest.round_indices[0], manifest.round_indices[0] + manifest.repetitions)
    ):
        raise SystemExit("Refresh requires consecutive original rounds")
    if manifest.round_seeds != list(
        range(manifest.round_seeds[0], manifest.round_seeds[0] + manifest.repetitions)
    ):
        raise SystemExit("Refresh requires consecutive original seeds")
    directory = Path(tempfile.mkdtemp(prefix="refresh-", dir=args.manifest.parent))
    if args.references_only:
        load_local_runtime_environment(PROJECT_ROOT / ".env")
        config = load_experiment_configuration(args.config)

        async def preflight() -> None:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    headless=manifest.headless,
                    executable_path=str(configured_executable(config.browser.executable_path_env)),
                )
                try:
                    for path in args.task_path:
                        for index in range(manifest.repetitions):
                            artifact, passed = await run_reference_trial(
                                browser,
                                load_task(path),
                                directory,
                                restrict_network=manifest.rendering_profile == "strict",
                                viewport={"width": 1920, "height": 1080}
                                if manifest.rendering_profile == "visual-parity"
                                else None,
                            )
                            print(
                                f"{path.name} repetition={index + 1} passed={passed} {artifact}",
                                flush=True,
                            )
                finally:
                    await browser.close()

        asyncio.run(preflight())
        return

    # Delegate normal trials to the existing CLI so runners, budgets and manifest stay aligned.
    from browser_agent_evaluation.cli.repeat import main as repeat_main

    limits = manifest.limits
    command = [
        "--config",
        str(args.config),
        "--output-dir",
        str(directory),
        "--task-path",
        *map(str, args.task_path),
        "--runners",
        *manifest.ai_runners,
        "--model",
        manifest.model,
        "--repetitions",
        str(manifest.repetitions),
        "--round",
        str(manifest.round_indices[0]),
        "--seed",
        str(manifest.round_seeds[0] - manifest.round_indices[0] + 1),
        "--task-language",
        manifest.task_language,
        "--rendering-profile",
        manifest.rendering_profile,
        "--headless" if manifest.headless else "--no-headless",
        "--max-requests-per-trial",
        str(limits.max_requests_per_trial),
    ]
    if limits.max_total_usd_per_round is not None:
        command += [
            "--max-total-usd",
            str(limits.max_total_usd_per_round),
            "--max-trial-usd",
            str(limits.max_trial_usd),
        ]
    if limits.max_tokens_per_trial is not None:
        command += ["--max-tokens-per-trial", str(limits.max_tokens_per_trial)]
    if manifest.skip_ai_on_reference_failure:
        raise SystemExit("Selective refresh requires the always-run-AI policy")
    repeat_main(command)
    replacement = load_repeated_evidence(directory / "run-manifest.json")
    if replacement.manifest.provider_endpoint != manifest.provider_endpoint:
        raise SystemExit("Provider endpoint changed; replacement preserved separately")
    retained = [
        record.path.name for record in original.records if record.trial.task_id not in selected
    ]
    for record in replacement.records:
        destination = args.manifest.parent / record.path.name
        if destination.exists():
            raise SystemExit(f"Evidence filename collision: {destination}")
        shutil.copy2(record.path, destination)
    shutil.copy2(args.manifest, directory / "previous-manifest.json")
    updated_tasks = {task.id: task for task in replacement.manifest.tasks}
    updated = manifest.model_copy(
        update={
            "tasks": [updated_tasks.get(task.id, task) for task in manifest.tasks],
            "artifact_files": retained + [record.path.name for record in replacement.records],
            "execution_notes": manifest.execution_notes
            + [
                f"Selective rerun at {now_utc().isoformat()}: {', '.join(sorted(selected))}. "
                "Other task evidence retained. Earlier artifacts and manifest backed up locally."
            ],
        }
    )
    write_evaluation_manifest(updated, output_dir=args.manifest.parent)
    load_repeated_evidence(args.manifest)
    print(f"Updated {args.manifest}; backup and replacement run: {directory}")
