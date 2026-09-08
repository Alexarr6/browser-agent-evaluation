from __future__ import annotations

from pathlib import Path

from browser_agent_evaluation.evaluation.playwright_mcp_trial import task_origins
from browser_agent_evaluation.evaluation.rounds import (
    AI_RUNNERS,
    ENGLISH_TASK_PATHS,
    STANDARD_ENGLISH_TASK_PATHS,
    TASK_PATHS,
    _should_skip_ai_after_reference,
    build_round_plan,
)
from browser_agent_evaluation.evaluation.tasks import load_task


def test_round_plan_is_seeded_and_covers_each_runner_once() -> None:
    tasks = [load_task(path) for path in TASK_PATHS]

    first = build_round_plan(tasks, seed=20260824)
    second = build_round_plan(tasks, seed=20260824)

    assert first == second
    assert {item.task.id for item in first} == {task.id for task in tasks}
    assert all(set(item.runners) == set(AI_RUNNERS) for item in first)
    assert all(len(item.runners) == len(AI_RUNNERS) for item in first)


def test_round_plan_can_select_only_browser_use() -> None:
    tasks = [load_task(path) for path in ENGLISH_TASK_PATHS]

    plan = build_round_plan(tasks, seed=20260902, runners=("browser_use",))

    assert all(item.runners == ("browser_use",) for item in plan)


def test_english_round_tasks_are_available_with_the_same_arms() -> None:
    tasks = [load_task(path) for path in STANDARD_ENGLISH_TASK_PATHS]

    assert {task.id.removesuffix("-en") for task in tasks} == {
        load_task(path).id for path in TASK_PATHS
    }
    assert all(set(item.runners) == set(AI_RUNNERS) for item in build_round_plan(tasks, seed=1))


def test_default_english_matrix_includes_open_ended_experimental_tasks() -> None:
    task_ids = {load_task(path).id for path in ENGLISH_TASK_PATHS}

    assert {
        "marca-real-madrid-open-en",
        "amazon-cheapest-coffee-beans-en",
    }.issubset(task_ids)
    assert len(task_ids) == 7


def test_mcp_allowed_origins_include_every_task_domain() -> None:
    mdn = load_task(Path(__file__).parents[1] / "tasks/mdn-reference.yaml")
    wikipedia = load_task(Path(__file__).parents[1] / "tasks/en/wikipedia-search-en.yaml")

    assert task_origins(mdn) == "https://developer.mozilla.org"
    assert task_origins(wikipedia) == "https://www.wikipedia.org;https://en.wikipedia.org"


def test_open_control_failure_never_skips_ai_agents() -> None:
    root = Path(__file__).parents[1]
    standard = load_task(root / "tasks/en/mdn-reference-en.yaml")
    open_task = load_task(root / "tasks/experimental/marca-real-madrid-open-en.yaml")

    assert _should_skip_ai_after_reference(
        task=standard,
        reference_passed=False,
        skip_ai_on_reference_failure=True,
    )
    assert not _should_skip_ai_after_reference(
        task=open_task,
        reference_passed=False,
        skip_ai_on_reference_failure=True,
    )


def test_round_plan_changes_order_with_a_different_seed() -> None:
    tasks = [load_task(path) for path in TASK_PATHS]

    first = build_round_plan(tasks, seed=20260824)
    second = build_round_plan(tasks, seed=20260825)

    assert first != second
