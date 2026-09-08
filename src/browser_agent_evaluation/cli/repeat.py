from __future__ import annotations

import argparse
import asyncio
import os
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from browser_agent_evaluation.browser.binaries import configured_executable, executable_version
from browser_agent_evaluation.browser.environment import load_local_runtime_environment
from browser_agent_evaluation.configuration.loader import load_experiment_configuration
from browser_agent_evaluation.configuration.paths import PROJECT_ROOT
from browser_agent_evaluation.core.models import now_utc
from browser_agent_evaluation.evaluation.rounds import (
    AI_RUNNERS,
    ENGLISH_TASK_PATHS,
    TASK_PATHS,
    run_round,
)
from browser_agent_evaluation.evaluation.tasks import load_task
from browser_agent_evaluation.reporting.manifest import (
    AiRunnerName,
    EvaluationManifest,
    ManifestLimits,
    manifest_task,
    write_evaluation_manifest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="browser-eval repeat",
        description="Run randomized browser-agent evaluation rounds",
    )
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "experiment.yaml")
    parser.add_argument("--round", type=int, default=1, help="first round index")
    parser.add_argument("--repetitions", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--task-language", choices=("es", "en"), default=None)
    parser.add_argument("--max-total-usd", type=float, default=None)
    parser.add_argument("--max-trial-usd", type=float, default=None)
    parser.add_argument("--max-requests-per-trial", type=int, default=None)
    parser.add_argument("--max-tokens-per-trial", type=int, default=None)
    parser.add_argument("--runners", nargs="+", choices=AI_RUNNERS, default=None)
    parser.add_argument(
        "--model",
        "--browser-use-model",
        dest="model",
        default=None,
        help="common model for every AI runner; --browser-use-model is a legacy alias",
    )
    parser.add_argument(
        "--rendering-profile",
        choices=("strict", "visual-parity"),
        default="strict",
        help="strict blocks cross-origin assets; visual-parity loads them and fixes the viewport",
    )
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="override the configured browser visibility for every runner",
    )
    parser.add_argument(
        "--skip-ai-on-reference-failure",
        action="store_true",
        help="save budget by skipping AI runners when the deterministic reference fails",
    )
    parser.add_argument(
        "--task-path",
        nargs="+",
        type=Path,
        help="explicit task YAML path(s), overriding the configured English task matrix",
    )
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    load_local_runtime_environment(PROJECT_ROOT / ".env")
    configuration = load_experiment_configuration(args.config)
    api_key = os.environ.get(configuration.provider.api_key_env, "")
    if not api_key:
        raise SystemExit(
            f"{configuration.provider.api_key_env} is required for the approved repeated pilot"
        )
    if args.round < 1:
        raise SystemExit("--round must be positive")
    repetitions = (
        args.repetitions if args.repetitions is not None else configuration.execution.repetitions
    )
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
    reference_chromium = configured_executable(configuration.browser.executable_path_env)
    browser_use_chromium = configured_executable(
        configuration.browser.browser_use_executable_path_env
    )
    task_paths = list(
        args.task_path
        if args.task_path is not None
        else (ENGLISH_TASK_PATHS if task_language == "en" else TASK_PATHS)
    )
    tasks = [load_task(path) for path in task_paths]
    model = args.model or configuration.runners.browser_use.model
    headless = configuration.browser.headless if args.headless is None else args.headless
    max_requests_per_trial = (
        args.max_requests_per_trial
        if args.max_requests_per_trial is not None
        else configuration.execution.max_requests_per_run
    )
    max_tokens_per_trial = (
        args.max_tokens_per_trial
        if args.max_tokens_per_trial is not None
        else configuration.budget.max_tokens_per_run
    )
    output_dir = args.output_dir or PROJECT_ROOT / "runs/repeated" / task_language
    all_artifacts: list[Path] = []
    round_indices = list(range(args.round, args.round + repetitions))
    base_seed = args.seed if args.seed is not None else configuration.execution.seed
    round_seeds = [base_seed + round_index - 1 for round_index in round_indices]
    for round_index, round_seed in zip(round_indices, round_seeds, strict=True):
        all_artifacts.extend(
            asyncio.run(
                run_round(
                    tasks=tasks,
                    output_dir=output_dir,
                    api_key=api_key,
                    seed=round_seed,
                    round_index=round_index,
                    max_total_usd=max_total_usd,
                    max_trial_usd=max_trial_usd,
                    max_requests_per_trial=max_requests_per_trial,
                    max_tokens_per_trial=max_tokens_per_trial,
                    reference_chromium=reference_chromium,
                    browser_use_chromium=browser_use_chromium,
                    runners=runners,
                    model=model,
                    provider_endpoint=configuration.provider.endpoint,
                    headless=headless,
                    rendering_profile=args.rendering_profile,
                    skip_ai_on_reference_failure=args.skip_ai_on_reference_failure,
                )
            )
        )
    manifest = EvaluationManifest(
        created_at=now_utc(),
        task_language=task_language,
        tasks=[
            manifest_task(
                task_id=task.id,
                category=("experimental" if path.parent.name == "experimental" else "standard"),
                source=path,
                max_actions=task.max_actions,
                timeout_seconds=task.timeout_seconds,
                acceptance_fields=[
                    field
                    for field, value in task.acceptance.model_dump().items()
                    if value is not None
                ],
                verification_mode=task.verification_mode,
                verifier=task.acceptance.verifier,
            )
            for path, task in zip(task_paths, tasks, strict=True)
        ],
        ai_runners=[cast(AiRunnerName, runner) for runner in runners],
        repetitions=repetitions,
        round_indices=round_indices,
        round_seeds=round_seeds,
        model=model,
        provider_endpoint=configuration.provider.endpoint,
        reference_browser_version=executable_version(reference_chromium),
        browser_use_browser_version=executable_version(browser_use_chromium),
        rendering_profile=args.rendering_profile,
        headless=headless,
        skip_ai_on_reference_failure=args.skip_ai_on_reference_failure,
        limits=ManifestLimits(
            max_total_usd_per_round=max_total_usd,
            max_trial_usd=max_trial_usd,
            max_requests_per_trial=max_requests_per_trial,
            max_tokens_per_trial=max_tokens_per_trial,
        ),
        artifact_files=[path.name for path in all_artifacts],
    )
    manifest_path = write_evaluation_manifest(manifest, output_dir=output_dir)
    print("\n".join(str(path) for path in (*all_artifacts, manifest_path)))
