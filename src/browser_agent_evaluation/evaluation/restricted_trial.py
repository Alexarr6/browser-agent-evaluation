from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import httpx

from browser_agent_evaluation.agents.restricted.agent import AgentOutcome, RestrictedBrowserAgent
from browser_agent_evaluation.browser.session import new_controller
from browser_agent_evaluation.core.assertions import evaluate_acceptance
from browser_agent_evaluation.core.budget import ModelBudget
from browser_agent_evaluation.core.models import (
    TaskSpec,
    TrialEvidence,
    UsageEvidence,
    acceptance_outcome,
)
from browser_agent_evaluation.providers.chat_completions import (
    DEFAULT_MODEL,
    ChatCompletionsPlanner,
)
from browser_agent_evaluation.reporting.evidence import write_trial_evidence


async def run_restricted_trial(
    browser: object,
    task: TaskSpec,
    output_dir: Path,
    api_key: str,
    *,
    budget: ModelBudget | None = None,
    trial_id: str | None = None,
    restrict_network: bool = True,
    viewport: dict[str, int] | None = None,
    progress: Callable[[str], None] | None = None,
    provider_endpoint: str,
    model: str = DEFAULT_MODEL,
) -> Path:
    started = _now()
    trial_id = trial_id or f"restricted-{uuid.uuid4().hex[:12]}"
    budget = budget or ModelBudget(
        max_total_usd=4.75, max_trial_usd=0.25, max_requests_per_trial=12
    )
    budget.start_trial(trial_id)
    controller, context = await new_controller(
        browser, task, restrict_network=restrict_network, viewport=viewport
    )
    planner: ChatCompletionsPlanner | None = None
    outcome: AgentOutcome | None = None
    assertions: dict[str, bool] = {}
    failure: Exception | None = None
    verification_evidence: dict[str, str] = {}
    try:
        await controller.navigate(task.start_url)
        async with httpx.AsyncClient() as client:
            planner = ChatCompletionsPlanner(
                api_key=api_key,
                budget=budget,
                trial_id=trial_id,
                client=client,
                model=model,
                endpoint=provider_endpoint,
            )
            outcome = await RestrictedBrowserAgent(planner).run(task, controller, progress=progress)
        state = await controller.page_state()
        if task.acceptance.verifier:
            answer = json.loads(outcome.proposal_history[-1]).get("result", "")
            facts = await controller.verification_facts()
            state = replace(state, facts=facts, answer=answer)
            verification_evidence = {**facts, "answer": answer}
        assertions = evaluate_acceptance(task.acceptance, state)
    except Exception as error:
        failure = error
    finally:
        await context.close()  # type: ignore[attr-defined]
    ended = _now()
    passed = failure is None and outcome is not None and outcome.terminal_reason == "complete"
    if passed:
        passed = all(assertions.values())
    evidence = TrialEvidence(
        trial_id=trial_id,
        task_id=task.id,
        runner="restricted",
        started_at=started,
        ended_at=ended,
        duration_ms=_duration_ms(started, ended),
        outcome=acceptance_outcome(task, accepted=passed),
        action_count=outcome.action_count if outcome else 0,
        retry_count=0,
        cleanup_verified=True,
        assertion_results=assertions,
        verification_evidence=verification_evidence,
        policy_events=[]
        if passed
        else [outcome.terminal_reason if outcome else type(failure).__name__],
        observation_mode="accessibility_dom",
        usage=planner.usage if planner else _unavailable_usage(),
    )
    trace = "\n".join(outcome.proposal_history) if outcome else str(failure)[:500]
    return write_trial_evidence(
        evidence,
        output_dir=output_dir,
        raw_trace=trace,
        markers=[api_key],
        forbidden_paths=[str(Path.home())],
        max_trace_bytes=8_000,
    )


def _unavailable_usage() -> UsageEvidence:
    return UsageEvidence(
        prompt_tokens=None,
        completion_tokens=None,
        request_count=0,
        cost_usd=None,
        unavailable_reason="planner initialization failed",
    )


def _now() -> datetime:
    return datetime.now(UTC)


def _duration_ms(started: datetime, ended: datetime) -> int:
    return int((ended - started).total_seconds() * 1_000)
