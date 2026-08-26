from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from browser_agent_evaluation.browser.executor import BrowserController, execute_action
from browser_agent_evaluation.core.budget import BudgetExceeded
from browser_agent_evaluation.core.models import BrowserActionProposal, ExpectedState, TaskSpec
from browser_agent_evaluation.core.policy import validate_action


class BrowserPlanner(Protocol):
    async def propose(
        self,
        *,
        task: TaskSpec,
        observation: str,
        action_history: tuple[str, ...],
        remaining_actions: int,
    ) -> BrowserActionProposal: ...


def _expected_state_matches(expected: ExpectedState, *, before: str, after: str) -> bool:
    if expected.kind == "url_or_text_changes":
        return after != before
    if expected.kind in {"url_contains", "text_visible", "value_equals"}:
        return expected.value in after
    return False


@dataclass(frozen=True)
class AgentOutcome:
    action_count: int
    terminal_reason: str
    action_history: tuple[str, ...]
    proposal_history: tuple[str, ...]


class RestrictedBrowserAgent:
    def __init__(self, planner: BrowserPlanner) -> None:
        self.planner = planner

    async def run(
        self,
        task: TaskSpec,
        browser: BrowserController,
        *,
        progress: Callable[[str], None] | None = None,
    ) -> AgentOutcome:
        history: list[str] = []
        proposals: list[str] = []
        pending_expected_state: str | None = None
        execution_recoveries = 0
        for action_count in range(task.max_actions):
            raw_observation = await browser.observe()
            observation = raw_observation
            if pending_expected_state:
                observation += (
                    "\n\nPlanner note: the previous expected state was not observed yet. "
                    f"Use a bounded recovery action if needed: {pending_expected_state}"
                )
            self._emit(progress, f"planning turn {action_count + 1}/{task.max_actions}")
            try:
                proposal = await self.planner.propose(
                    task=task,
                    observation=observation,
                    action_history=tuple(history),
                    remaining_actions=task.max_actions - action_count,
                )
            except BudgetExceeded:
                return self._outcome(action_count, "planner_budget_exceeded", history, proposals)
            proposals.append(proposal.model_dump_json(exclude_none=True))
            if proposal.step_status != "in_progress":
                self._emit(progress, f"terminal status: {proposal.step_status}")
                return self._outcome(action_count, proposal.step_status, history, proposals)
            if proposal.action is None:
                return self._outcome(action_count, "invalid_proposal", history, proposals)
            decision = validate_action(task, proposal.action)
            if not decision.allowed:
                self._emit(progress, f"policy denied: {decision.reason}")
                return self._outcome(action_count, decision.reason, history, proposals)
            action_fingerprint = proposal.action.model_dump_json(exclude_none=True)
            if history and action_fingerprint == history[-1]:
                return self._outcome(action_count, "non_progress", history, proposals)
            self._emit(
                progress, f"action {action_count + 1}/{task.max_actions}: {proposal.action.type}"
            )
            try:
                await execute_action(browser, proposal.action)
            except Exception as error:
                history.append(action_fingerprint)
                execution_recoveries += 1
                if execution_recoveries > 2:
                    return self._outcome(
                        action_count + 1,
                        f"execution_recovery_exhausted:{type(error).__name__}:{str(error)[:200]}",
                        history,
                        proposals,
                    )
                pending_expected_state = (
                    "The previous action could not find or operate its semantic target. "
                    "Inspect the current observation and choose a different, visible "
                    "semantic target; do not repeat the failed action."
                )
                self._emit(
                    progress,
                    f"action failed ({type(error).__name__}); recovery {execution_recoveries}/2",
                )
                continue
            history.append(action_fingerprint)
            if proposal.expected_state is not None:
                after_observation = await browser.observe()
                if _expected_state_matches(
                    proposal.expected_state, before=raw_observation, after=after_observation
                ):
                    pending_expected_state = None
                else:
                    pending_expected_state = (
                        f"{proposal.expected_state.kind}={proposal.expected_state.value!r}"
                    )
        return self._outcome(task.max_actions, "action_cap", history, proposals)

    @staticmethod
    def _emit(progress: Callable[[str], None] | None, message: str) -> None:
        if progress is not None:
            progress(message)

    @staticmethod
    def _outcome(
        action_count: int,
        terminal_reason: str,
        history: list[str],
        proposals: list[str],
    ) -> AgentOutcome:
        return AgentOutcome(
            action_count=action_count,
            terminal_reason=terminal_reason,
            action_history=tuple(history),
            proposal_history=tuple(proposals),
        )
