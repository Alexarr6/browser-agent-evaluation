from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from browser_agent_evaluation.agents.reference import PlaywrightReferenceRunner
from browser_agent_evaluation.core.assertions import PageState
from browser_agent_evaluation.core.models import (
    AcceptanceSpec,
    ActionTarget,
    RestrictedBrowserAction,
    TaskPolicy,
    TaskSpec,
)
from browser_agent_evaluation.evaluation.tasks import load_task, reference_actions


class FakeExecutor:
    def __init__(self) -> None:
        self.actions: list[str] = []

    async def execute(self, action: RestrictedBrowserAction) -> None:
        self.actions.append(action.type)

    async def page_state(self) -> PageState:
        return PageState(
            url="https://en.wikipedia.org/wiki/Playwright",
            title="Playwright - Wikipedia",
            visible_text="Playwright",
            input_values={},
        )


@pytest.fixture
def task_spec() -> TaskSpec:
    return TaskSpec(
        schema_version=1,
        id="wikipedia-search",
        start_url="https://www.wikipedia.org/",
        instruction="1. Busca Playwright.\n2. Abre el artículo principal.\n3. Termina.",
        completion="La página final muestra el artículo solicitado.",
        policy=TaskPolicy(allowed_domains=["www.wikipedia.org"], risk="read_only"),
        max_actions=12,
        timeout_seconds=60,
        acceptance=AcceptanceSpec(page_title="Playwright"),
    )


def test_english_reference_recipes_match_spanish_action_shapes() -> None:
    spanish_root = Path(__file__).parents[1] / "tasks"
    english_root = spanish_root / "en"

    for spanish_path in sorted(spanish_root.glob("*.yaml")):
        english_path = english_root / spanish_path.name.replace(".yaml", "-en.yaml")
        spanish_actions = reference_actions(load_task(spanish_path))
        english_actions = reference_actions(load_task(english_path))
        assert [action.type for action in english_actions] == [
            action.type for action in spanish_actions
        ]


@pytest.mark.parametrize(
    "filename",
    [
        "marca-real-madrid-open-en.yaml",
        "amazon-cheapest-coffee-beans-en.yaml",
    ],
)
def test_open_ended_references_only_check_landing_page_reachability(filename: str) -> None:
    path = Path(__file__).parents[1] / "tasks/experimental" / filename
    actions = reference_actions(load_task(path))

    assert [action.type for action in actions] == ["navigate"]


def test_selenium_reference_recipes_have_bounded_multi_action_shape() -> None:
    root = Path(__file__).parents[1] / "tasks"
    expected = {
        "selenium-web-form.yaml": (8, "click"),
        "selenium-ajax-labels.yaml": (7, "wait"),
        "selenium-key-events.yaml": (8, "press"),
    }

    for filename, (count, final_action) in expected.items():
        actions = reference_actions(load_task(root / filename))
        assert len(actions) == count
        assert actions[0].type == "navigate"
        assert actions[-1].type == final_action


def test_reference_runner_uses_independent_acceptance(task_spec: TaskSpec) -> None:
    executor = FakeExecutor()
    result = asyncio.run(
        PlaywrightReferenceRunner(executor).run(
            task_spec,
            [
                RestrictedBrowserAction(
                    type="click", target=ActionTarget(role="button", name="Search")
                )
            ],
        )
    )

    assert executor.actions == ["click"]
    assert result.passed is True
    assert result.assertions["page_title"] is True
