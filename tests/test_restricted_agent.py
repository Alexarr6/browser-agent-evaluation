from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from browser_agent_evaluation.agents.restricted.agent import RestrictedBrowserAgent
from browser_agent_evaluation.core.models import (
    AcceptanceSpec,
    ActionTarget,
    BrowserActionProposal,
    ExpectedState,
    RestrictedBrowserAction,
    TaskPolicy,
    TaskSpec,
)


class FakeBrowser:
    def __init__(self) -> None:
        self.url = "https://www.wikipedia.org/"
        self.clicked: list[str] = []

    async def observe(self) -> str:
        return "button: Search; textbox: Search Wikipedia"

    async def click(self, target: ActionTarget) -> None:
        self.clicked.append(target.name or "")

    async def wait(self) -> None:
        return None


class OneActionPlanner:
    async def propose(self, **_: object) -> BrowserActionProposal:
        return BrowserActionProposal(
            step_index=1,
            step_status="in_progress",
            action=RestrictedBrowserAction(
                type="click", target=ActionTarget(role="button", name="Search")
            ),
        )


def task() -> TaskSpec:
    return TaskSpec(
        schema_version=1,
        id="wikipedia-search",
        start_url="https://www.wikipedia.org/",
        instruction="1. Pulsa Buscar.\n2. Termina.",
        completion="La búsqueda está iniciada.",
        policy=TaskPolicy(allowed_domains=["www.wikipedia.org"], risk="read_only"),
        max_actions=2,
        timeout_seconds=60,
        acceptance=AcceptanceSpec(page_title="Wikipedia"),
    )


def test_restricted_agent_executes_only_validated_action() -> None:
    browser = FakeBrowser()
    outcome = asyncio.run(RestrictedBrowserAgent(OneActionPlanner()).run(task(), browser))

    assert browser.clicked == ["Search"]
    assert outcome.action_count == 1
    assert outcome.terminal_reason == "non_progress"
    assert len(outcome.proposal_history) == 2


def test_repeated_action_is_allowed_after_intervening_progress() -> None:
    actions = [
        RestrictedBrowserAction(
            type="click", target=ActionTarget(role="button", name="Search")
        ),
        RestrictedBrowserAction(
            type="click", target=ActionTarget(role="button", name="Other")
        ),
        RestrictedBrowserAction(
            type="click", target=ActionTarget(role="button", name="Search")
        ),
    ]

    class SequencePlanner:
        index = 0

        async def propose(self, **_: object) -> BrowserActionProposal:
            if self.index == len(actions):
                return BrowserActionProposal(step_index=4, step_status="complete")
            action = actions[self.index]
            self.index += 1
            return BrowserActionProposal(
                step_index=self.index, step_status="in_progress", action=action
            )

    extended_task = task().model_copy(update={"max_actions": 4})
    browser = FakeBrowser()
    outcome = asyncio.run(RestrictedBrowserAgent(SequencePlanner()).run(extended_task, browser))

    assert browser.clicked == ["Search", "Other", "Search"]
    assert outcome.terminal_reason == "complete"


def test_expected_state_is_checked_after_each_executed_action() -> None:
    class ChangingBrowser(FakeBrowser):
        observations = iter(("before", "Done!", "Done!"))

        async def observe(self) -> str:
            return next(self.observations)

    class ExpectedStatePlanner:
        calls = 0

        async def propose(self, **_: object) -> BrowserActionProposal:
            self.calls += 1
            if self.calls == 1:
                return BrowserActionProposal(
                    step_index=1,
                    step_status="in_progress",
                    action=RestrictedBrowserAction(
                        type="click", target=ActionTarget(role="button", name="Search")
                    ),
                    expected_state=ExpectedState(kind="text_visible", value="Done!"),
                )
            return BrowserActionProposal(step_index=2, step_status="complete")

    outcome = asyncio.run(
        RestrictedBrowserAgent(ExpectedStatePlanner()).run(
            task(), ChangingBrowser()
        )
    )

    assert outcome.terminal_reason == "complete"
    assert outcome.action_count == 1


def test_expected_state_mismatch_allows_a_bounded_recovery_action() -> None:
    class RecoveringBrowser(FakeBrowser):
        observations = iter(("before", "Updating", "Updating", "Done!", "Done!"))

        async def observe(self) -> str:
            return next(self.observations)

    class RecoveryPlanner:
        calls = 0

        async def propose(self, **_: object) -> BrowserActionProposal:
            self.calls += 1
            if self.calls == 1:
                return BrowserActionProposal(
                    step_index=1,
                    step_status="in_progress",
                    action=RestrictedBrowserAction(
                        type="click", target=ActionTarget(role="button", name="Add Label")
                    ),
                    expected_state=ExpectedState(kind="text_visible", value="Done!"),
                )
            if self.calls == 2:
                return BrowserActionProposal(
                    step_index=2,
                    step_status="in_progress",
                    action=RestrictedBrowserAction(type="wait"),
                    expected_state=ExpectedState(kind="text_visible", value="Done!"),
                )
            return BrowserActionProposal(step_index=3, step_status="complete")

    outcome = asyncio.run(
        RestrictedBrowserAgent(RecoveryPlanner()).run(
            task().model_copy(update={"max_actions": 3}), RecoveringBrowser()
        )
    )

    assert outcome.terminal_reason == "complete"
    assert outcome.action_count == 2


def test_restricted_agent_recovers_once_from_a_stale_semantic_target() -> None:
    class RecoveringBrowser(FakeBrowser):
        async def click(self, target: ActionTarget) -> None:
            if target.name == "Stale":
                raise RuntimeError("target no longer exists")
            await super().click(target)

    class RecoveryPlanner:
        calls = 0

        async def propose(self, **_: object) -> BrowserActionProposal:
            self.calls += 1
            if self.calls == 1:
                return BrowserActionProposal(
                    step_index=1,
                    step_status="in_progress",
                    action=RestrictedBrowserAction(
                        type="click", target=ActionTarget(role="button", name="Stale")
                    ),
                )
            if self.calls == 2:
                return BrowserActionProposal(
                    step_index=2,
                    step_status="in_progress",
                    action=RestrictedBrowserAction(
                        type="click", target=ActionTarget(role="button", name="Search")
                    ),
                )
            return BrowserActionProposal(step_index=3, step_status="complete")

    progress: list[str] = []
    outcome = asyncio.run(
        RestrictedBrowserAgent(RecoveryPlanner()).run(
            task().model_copy(update={"max_actions": 3}),
            RecoveringBrowser(),
            progress=progress.append,
        )
    )

    assert outcome.terminal_reason == "complete"
    assert outcome.action_count == 2
    assert any("recovery" in message for message in progress)


def test_invalid_planner_json_is_rejected_before_browser_use() -> None:
    with pytest.raises(ValidationError):
        BrowserActionProposal.model_validate(
            {"step_index": 1, "step_status": "in_progress", "action": {"type": "evaluate"}}
        )


def test_restricted_agent_stops_on_policy_denial() -> None:
    class UnsafePlanner:
        async def propose(self, **_: object) -> BrowserActionProposal:
            return BrowserActionProposal(
                step_index=1,
                step_status="in_progress",
                action=RestrictedBrowserAction(type="navigate", value="https://example.com"),
            )

    outcome = asyncio.run(RestrictedBrowserAgent(UnsafePlanner()).run(task(), FakeBrowser()))

    assert outcome.terminal_reason == "domain_not_allowed"
    assert outcome.action_count == 0
