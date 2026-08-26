from __future__ import annotations

import pytest
from pydantic import ValidationError

from browser_agent_evaluation.models import (
    AcceptanceSpec,
    ActionTarget,
    BrowserActionProposal,
    RestrictedBrowserAction,
    TaskPolicy,
    TaskSpec,
    create_runner_input,
    render_runner_instruction,
)


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


def test_runner_prompt_excludes_hidden_acceptance() -> None:
    prompt = render_runner_instruction(task_spec())

    assert "Busca Playwright" in prompt
    assert "www.wikipedia.org" in prompt
    assert "Playwright" not in prompt.split("Completion:", maxsplit=1)[-1]
    assert "page_title" not in prompt


@pytest.mark.parametrize(
    "runner",
    ["browser_use", "stagehand", "playwright_mcp", "restricted"],
)
def test_all_ai_arms_receive_identical_task_prompt_without_acceptance(runner: str) -> None:
    task = task_spec()
    runner_input = create_runner_input(task, runner=runner)  # type: ignore[arg-type]

    assert runner_input.prompt == render_runner_instruction(task)
    assert "page_title" not in runner_input.prompt


def test_task_requires_https_start_url_and_matching_domain() -> None:
    data = task_spec().model_dump()
    data["start_url"] = "http://example.test/"

    with pytest.raises(ValidationError, match="HTTPS"):
        TaskSpec.model_validate(data)

    data = task_spec().model_dump()
    data["start_url"] = "https://example.test/"
    with pytest.raises(ValidationError, match="allowlist"):
        TaskSpec.model_validate(data)


def test_action_requires_semantic_target_and_known_type() -> None:
    action = BrowserActionProposal(
        step_index=1,
        step_status="in_progress",
        action=RestrictedBrowserAction(
            type="click", target=ActionTarget(role="button", name="Search")
        ),
    )

    assert action.action.type == "click"
    with pytest.raises(ValidationError, match="semantic locator"):
        ActionTarget()
    with pytest.raises(ValidationError, match="Input should be"):
        RestrictedBrowserAction(type="evaluate", target=ActionTarget(text="x"))
