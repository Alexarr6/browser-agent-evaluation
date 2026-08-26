from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml
from playwright.async_api import async_playwright

from browser_agent_evaluation.assertions import evaluate_acceptance
from browser_agent_evaluation.budget import ModelBudget
from browser_agent_evaluation.evidence import write_trial_evidence
from browser_agent_evaluation.live_playwright import (
    LivePlaywrightController,
    LiveReferenceExecutor,
    restrict_page_network,
)
from browser_agent_evaluation.models import (
    RestrictedBrowserAction,
    TaskSpec,
    TrialEvidence,
    UsageEvidence,
)
from browser_agent_evaluation.provider import OpenRouterPlanner
from browser_agent_evaluation.restricted_agent import AgentOutcome, RestrictedBrowserAgent
from browser_agent_evaluation.runners.playwright_reference import PlaywrightReferenceRunner


def load_task(path: Path) -> TaskSpec:
    return TaskSpec.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


async def run_micro_pilot(*, task: TaskSpec, output_dir: Path, api_key: str) -> list[Path]:
    artifacts: list[Path] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            reference_artifact, reference_passed = await _run_reference(browser, task, output_dir)
            artifacts.append(reference_artifact)
            if not reference_passed:
                return artifacts
            artifacts.append(await _run_restricted(browser, task, output_dir, api_key))
        finally:
            await browser.close()
    return artifacts


async def _new_controller(
    browser: object,
    task: TaskSpec,
    *,
    restrict_network: bool = True,
    viewport: dict[str, int] | None = None,
) -> tuple[LivePlaywrightController, object]:
    context_options = {"viewport": viewport} if viewport is not None else {}
    context = await browser.new_context(**context_options)  # type: ignore[attr-defined]
    page = await context.new_page()
    if restrict_network:
        await restrict_page_network(page, allowed_domains=task.policy.allowed_domains)
    return LivePlaywrightController(page, allowed_domains=task.policy.allowed_domains), context


async def _run_reference(
    browser: object,
    task: TaskSpec,
    output_dir: Path,
    *,
    restrict_network: bool = True,
    viewport: dict[str, int] | None = None,
) -> tuple[Path, bool]:
    started = _now()
    controller, context = await _new_controller(
        browser, task, restrict_network=restrict_network, viewport=viewport
    )
    result = None
    failure: Exception | None = None
    try:
        runner = PlaywrightReferenceRunner(LiveReferenceExecutor(controller))
        result = await runner.run(task, _reference_actions(task))
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
        outcome="passed" if passed else "failed",
        action_count=result.action_count if result else 0,
        retry_count=0,
        cleanup_verified=True,
        assertion_results=result.assertions if result else {},
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


async def _run_restricted(
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
) -> Path:
    started = _now()
    trial_id = trial_id or f"restricted-{uuid.uuid4().hex[:12]}"
    budget = budget or ModelBudget(
        max_total_usd=4.75, max_trial_usd=0.25, max_requests_per_trial=12
    )
    budget.start_trial(trial_id)
    controller, context = await _new_controller(
        browser, task, restrict_network=restrict_network, viewport=viewport
    )
    planner: OpenRouterPlanner | None = None
    outcome: AgentOutcome | None = None
    assertions: dict[str, bool] = {}
    failure: Exception | None = None
    try:
        await controller.navigate(task.start_url)
        async with httpx.AsyncClient() as client:
            planner = OpenRouterPlanner(
                api_key=api_key, budget=budget, trial_id=trial_id, client=client
            )
            outcome = await RestrictedBrowserAgent(planner).run(
                task, controller, progress=progress
            )
        assertions = evaluate_acceptance(task.acceptance, await controller.page_state())
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
        outcome="passed" if passed else "failed",
        action_count=outcome.action_count if outcome else 0,
        retry_count=0,
        cleanup_verified=True,
        assertion_results=assertions,
        policy_events=[] if passed else [
            outcome.terminal_reason if outcome else type(failure).__name__
        ],
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


def _reference_actions(task: TaskSpec) -> list[RestrictedBrowserAction]:
    task_id = task.id.removesuffix("-en")
    if task_id in {"marca-real-madrid-open", "amazon-cheapest-coffee-beans"}:
        # These tasks are intentionally open-ended; the reference only verifies
        # that the public landing page is reachable before AI arms run.
        return [RestrictedBrowserAction(type="navigate", value=task.start_url)]
    if task_id == "wikipedia-search":
        return [
            RestrictedBrowserAction(type="navigate", value=task.start_url),
            RestrictedBrowserAction(
                type="fill", target={"label": "Search Wikipedia"}, value="Playwright"
            ),
            RestrictedBrowserAction(type="click", target={"role": "button", "name": "Search"}),
        ]
    if task_id == "mdn-reference":
        return [
            RestrictedBrowserAction(type="navigate", value=task.start_url),
            RestrictedBrowserAction(
                type="navigate", value="https://developer.mozilla.org/en-US/docs/Web/CSS/:has"
            ),
        ]
    if task_id == "selenium-web-form":
        return [
            RestrictedBrowserAction(type="navigate", value=task.start_url),
            RestrictedBrowserAction(
                type="fill", target={"label": "Text input"}, value="Ada Lovelace"
            ),
            RestrictedBrowserAction(
                type="fill", target={"label": "Textarea"}, value="Prueba sintética"
            ),
            RestrictedBrowserAction(
                type="select",
                target={"role": "combobox", "name": "Dropdown (select)"},
                value="2",
            ),
            RestrictedBrowserAction(
                type="fill",
                target={"role": "combobox", "name": "Dropdown (datalist)"},
                value="New York",
            ),
            RestrictedBrowserAction(type="check", target={"label": "Default checkbox"}),
            RestrictedBrowserAction(type="check", target={"label": "Default radio"}),
            RestrictedBrowserAction(
                type="click", target={"role": "button", "name": "Submit"}
            ),
        ]
    if task_id == "selenium-ajax-labels":
        field = {"role": "textbox"}
        button = {"role": "button", "name": "Add Label"}
        return [
            RestrictedBrowserAction(type="navigate", value=task.start_url),
            RestrictedBrowserAction(type="fill", target=field, value="Ada"),
            RestrictedBrowserAction(type="click", target=button),
            RestrictedBrowserAction(type="wait"),
            RestrictedBrowserAction(type="fill", target=field, value="Lovelace"),
            RestrictedBrowserAction(type="click", target=button),
            RestrictedBrowserAction(type="wait"),
        ]
    if task_id == "selenium-key-events":
        field = {"role": "textbox"}
        return [
            RestrictedBrowserAction(type="navigate", value=task.start_url),
            RestrictedBrowserAction(type="click", target=field),
            RestrictedBrowserAction(type="press", target=field, value="A"),
            RestrictedBrowserAction(type="press", target=field, value="d"),
            RestrictedBrowserAction(type="press", target=field, value="a"),
            RestrictedBrowserAction(type="press", target=field, value="ArrowLeft"),
            RestrictedBrowserAction(type="press", target=field, value="Backspace"),
            RestrictedBrowserAction(type="press", target=field, value="Tab"),
        ]
    raise ValueError(f"no deterministic reference recipe for task {task.id}")


def _now() -> datetime:
    return datetime.now(UTC)


def _duration_ms(started: datetime, ended: datetime) -> int:
    return int((ended - started).total_seconds() * 1_000)


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is required for the approved micro-pilot")
    experiment_root = Path(__file__).resolve().parents[2]
    task_path = Path(
        os.environ.get(
            "BROWSER_EVAL_TASK_PATH",
            str(experiment_root / "tasks/wikipedia-search.yaml"),
        )
    )
    task = load_task(task_path)
    artifacts = asyncio.run(
        run_micro_pilot(
            task=task,
            output_dir=experiment_root / "runs/micro-pilot",
            api_key=api_key,
        )
    )
    print("\n".join(str(path) for path in artifacts))


if __name__ == "__main__":
    main()
