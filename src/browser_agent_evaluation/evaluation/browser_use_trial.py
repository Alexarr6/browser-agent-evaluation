from __future__ import annotations

import asyncio
from pathlib import Path

from browser_agent_evaluation.agents.browser_use.runner import (
    BrowserUsePilotError,
    run_browser_use_task,
)
from browser_agent_evaluation.core.budget import ModelBudget
from browser_agent_evaluation.core.models import (
    TaskSpec,
    TrialEvidence,
    acceptance_outcome,
    now_utc,
)
from browser_agent_evaluation.reporting.evidence import write_trial_evidence


async def run_browser_use_trial(
    *,
    task: TaskSpec,
    output_dir: Path,
    api_key: str,
    budget: ModelBudget,
    trial_id: str,
    model_id: str,
    provider_endpoint: str,
    chromium_executable: Path,
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
                chromium_executable=chromium_executable,
                max_steps=task.max_actions,
                budget=budget,
                trial_id=trial_id,
                model=model_id,
                provider_endpoint=provider_endpoint,
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
        outcome=acceptance_outcome(task, accepted=passed),
        action_count=result.action_count,
        retry_count=0,
        cleanup_verified=True,
        assertion_results=result.assertion_results,
        verification_evidence=result.verification_evidence or {},
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


def _duration_ms(started: object, ended: object) -> int:
    return int((ended - started).total_seconds() * 1_000)  # type: ignore[operator]
