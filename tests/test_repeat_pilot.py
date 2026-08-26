from __future__ import annotations

from pathlib import Path

from browser_agent_evaluation.micro_pilot import load_task
from browser_agent_evaluation.repeat_pilot import (
    AI_RUNNERS,
    ENGLISH_TASK_PATHS,
    STANDARD_ENGLISH_TASK_PATHS,
    TASK_PATHS,
    _task_origins,
    build_round_plan,
)


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

    assert _task_origins(mdn) == "https://developer.mozilla.org"
    assert _task_origins(wikipedia) == "https://www.wikipedia.org;https://en.wikipedia.org"


def test_round_plan_changes_order_with_a_different_seed() -> None:
    tasks = [load_task(path) for path in TASK_PATHS]

    first = build_round_plan(tasks, seed=20260824)
    second = build_round_plan(tasks, seed=20260825)

    assert first != second
