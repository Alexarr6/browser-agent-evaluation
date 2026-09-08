from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from pathlib import Path

from browser_agent_evaluation.agents.reference import PlaywrightReferenceRunner
from browser_agent_evaluation.browser.playwright import LiveReferenceExecutor
from browser_agent_evaluation.browser.session import new_controller
from browser_agent_evaluation.core.models import (
    TaskSpec,
    TrialEvidence,
    UsageEvidence,
    acceptance_outcome,
)
from browser_agent_evaluation.evaluation.open_reference import run_open_reference
from browser_agent_evaluation.evaluation.tasks import reference_actions
from browser_agent_evaluation.reporting.evidence import write_trial_evidence


async def run_reference_trial(
    browser: object,
    task: TaskSpec,
    output_dir: Path,
    *,
    restrict_network: bool = True,
    viewport: dict[str, int] | None = None,
) -> tuple[Path, bool]:
    started = _now()
    controller, context = await new_controller(
        browser, task, restrict_network=restrict_network, viewport=viewport
    )
    result = None
    failure: Exception | None = None
    verification_evidence: dict[str, str] = {}
    try:
        runner = PlaywrightReferenceRunner(LiveReferenceExecutor(controller))
        if task.acceptance.verifier:
            result, verification_evidence = await asyncio.wait_for(
                run_open_reference(controller, task), timeout=task.timeout_seconds,
            )
        else:
            result = await runner.run(task, reference_actions(task))
    except Exception as error:
        failure = error
    finally:
        await context.close()  # type: ignore[attr-defined]
    ended = _now()
    passed = result is not None and result.passed
    evidence = TrialEvidence(
        trial_id=f"reference-{uuid.uuid4().hex[:12]}",
        task_id=task.id,
        runner="playwright_reference",
        started_at=started,
        ended_at=ended,
        duration_ms=_duration_ms(started, ended),
        outcome=acceptance_outcome(task, accepted=passed),
        action_count=result.action_count if result else 0,
        retry_count=0,
        cleanup_verified=True,
        assertion_results=result.assertions if result else {},
        verification_evidence=verification_evidence,
        policy_events=[] if passed else [type(failure).__name__ if failure else "reference_failed"],
        observation_mode="reference",
        usage=UsageEvidence(
            prompt_tokens=None,
            completion_tokens=None,
            request_count=0,
            cost_usd=None,
            unavailable_reason="reference run uses no model",
        ),
    )
    artifact = write_trial_evidence(
        evidence,
        output_dir=output_dir,
        raw_trace=result.terminal_reason if result else str(failure)[:500],
        markers=[],
        forbidden_paths=[str(Path.home())],
        max_trace_bytes=2_000,
    )
    return artifact, passed


def _now() -> datetime:
    return datetime.now(UTC)


def _duration_ms(started: datetime, ended: datetime) -> int:
    return int((ended - started).total_seconds() * 1_000)
