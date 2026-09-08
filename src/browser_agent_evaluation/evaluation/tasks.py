from __future__ import annotations

from pathlib import Path

import yaml

from browser_agent_evaluation.core.models import RestrictedBrowserAction, TaskSpec


def load_task(path: Path) -> TaskSpec:
    return TaskSpec.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def reference_actions(task: TaskSpec) -> list[RestrictedBrowserAction]:
    task_id = task.id.removesuffix("-en")
    if task.acceptance.verifier:
        raise ValueError("Open tasks require the dynamic reference recipe and independent verifier")
    if task_id == "wikipedia-search":
        return [
            RestrictedBrowserAction(type="navigate", value=task.start_url),
            RestrictedBrowserAction(
                type="select",
                target={"role": "combobox"},
                value="English" if task.id.endswith("-en") else "Español",
            ),
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
            RestrictedBrowserAction(type="click", target={"role": "button", "name": "Submit"}),
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
