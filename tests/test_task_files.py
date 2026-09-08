from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from browser_agent_evaluation.core.models import TaskSpec

TASKS_ROOT = Path(__file__).parents[1] / "tasks"
ENGLISH_TASKS_ROOT = TASKS_ROOT / "en"


def test_english_tasks_preserve_safety_contracts_with_larger_runtime_limits() -> None:
    spanish = {
        task.id: task
        for task in (
            TaskSpec.model_validate(yaml.safe_load(path.read_text("utf-8")))
            for path in sorted(TASKS_ROOT.glob("*.yaml"))
        )
    }
    english = {
        task.id.removesuffix("-en"): task
        for task in (
            TaskSpec.model_validate(yaml.safe_load(path.read_text("utf-8")))
            for path in sorted(ENGLISH_TASKS_ROOT.glob("*.yaml"))
        )
    }

    assert set(english) == set(spanish)
    for task_id, spanish_task in spanish.items():
        english_task = english[task_id]
        assert english_task.model_copy(update={"id": task_id}).model_dump(
            exclude={"instruction", "completion", "max_actions", "timeout_seconds"}
        ) == spanish_task.model_dump(
            exclude={"instruction", "completion", "max_actions", "timeout_seconds"}
        )
        assert english_task.max_actions == 48
        assert english_task.timeout_seconds == 300
        assert english_task.instruction.isascii()
        assert english_task.completion.isascii()


@pytest.mark.parametrize(
    ("filename", "allowed_domains"),
    [
        ("marca-real-madrid-open-en.yaml", ["www.marca.com", "marca.com"]),
        ("amazon-cheapest-coffee-beans-en.yaml", ["www.amazon.es", "amazon.es"]),
    ],
)
def test_experimental_open_ended_tasks_are_valid_and_safe(
    filename: str, allowed_domains: list[str]
) -> None:
    path = TASKS_ROOT / "experimental" / filename
    task = TaskSpec.model_validate(yaml.safe_load(path.read_text("utf-8")))

    assert task.policy.allowed_domains == allowed_domains
    assert task.policy.risk == "read_only"
    assert task.policy.allow_form_submit is False
    assert task.verification_mode == "task_completion"
    assert task.acceptance.verifier is not None
    assert "exact" in task.completion


def test_pending_public_tasks_are_valid_and_safe() -> None:
    tasks = [
        TaskSpec.model_validate(yaml.safe_load(path.read_text("utf-8")))
        for path in sorted(TASKS_ROOT.glob("*.yaml"))
    ]

    assert [task.id for task in tasks] == [
        "mdn-reference",
        "selenium-ajax-labels",
        "selenium-key-events",
        "selenium-web-form",
        "wikipedia-search",
    ]
    selenium_tasks = [task for task in tasks if task.id.startswith("selenium-")]
    assert all(task.max_actions == 24 for task in selenium_tasks)
    assert all(task.timeout_seconds == 90 for task in selenium_tasks)
    assert {task.id: task.policy.allow_form_submit for task in selenium_tasks} == {
        "selenium-ajax-labels": True,
        "selenium-key-events": False,
        "selenium-web-form": True,
    }
    interaction_counts = {
        task.id: sum(
            line.lstrip().split(".", 1)[0].isdigit()
            for line in task.instruction.splitlines()
        )
        - 1  # The final numbered line is independent verification, not an interaction.
        for task in selenium_tasks
    }
    assert interaction_counts == {
        "selenium-ajax-labels": 6,
        "selenium-key-events": 7,
        "selenium-web-form": 7,
    }


def test_every_atomic_task_file_declares_its_verification_mode_explicitly() -> None:
    for path in sorted(TASKS_ROOT.rglob("*.yaml")):
        payload = yaml.safe_load(path.read_text("utf-8"))
        if "instruction" not in payload:
            continue

        assert payload["verification_mode"] in {"task_completion", "reachability"}, path
