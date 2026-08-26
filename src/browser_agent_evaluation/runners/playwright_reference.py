from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from browser_agent_evaluation.assertions import PageState, evaluate_acceptance
from browser_agent_evaluation.models import RestrictedBrowserAction, TaskSpec
from browser_agent_evaluation.policy import validate_action


class ReferenceExecutor(Protocol):
    async def execute(self, action: RestrictedBrowserAction) -> None: ...
    async def page_state(self) -> PageState: ...


@dataclass(frozen=True)
class ReferenceResult:
    passed: bool
    assertions: dict[str, bool]
    action_count: int
    terminal_reason: str


class PlaywrightReferenceRunner:
    """Deterministic reference contract; concrete Playwright binding is optional later."""

    def __init__(self, executor: ReferenceExecutor) -> None:
        self.executor = executor

    async def run(
        self, task: TaskSpec, actions: list[RestrictedBrowserAction]
    ) -> ReferenceResult:
        for index, action in enumerate(actions, start=1):
            if index > task.max_actions:
                return ReferenceResult(False, {}, index - 1, "action_cap")
            decision = validate_action(task, action)
            if not decision.allowed:
                return ReferenceResult(False, {}, index - 1, decision.reason)
            await self.executor.execute(action)
        assertions = evaluate_acceptance(task.acceptance, await self.executor.page_state())
        return ReferenceResult(
            passed=all(assertions.values()),
            assertions=assertions,
            action_count=len(actions),
            terminal_reason="accepted" if all(assertions.values()) else "acceptance_failed",
        )
