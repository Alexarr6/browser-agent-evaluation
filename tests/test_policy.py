from __future__ import annotations

from pathlib import Path

from browser_agent_evaluation.core.models import ActionTarget, RestrictedBrowserAction, TaskSpec
from browser_agent_evaluation.core.policy import validate_action
from browser_agent_evaluation.evaluation.tasks import load_task


def task() -> TaskSpec:
    return TaskSpec.model_validate(
        {
            "schema_version": 1,
            "id": "selenium-form",
            "start_url": "https://www.selenium.dev/selenium/web/web-form.html",
            "instruction": "1. Rellena el formulario de prueba.\n2. Termina.",
            "completion": "El formulario de prueba muestra la respuesta.",
            "policy": {
                "allowed_domains": ["www.selenium.dev"],
                "risk": "synthetic_form",
                "allow_form_submit": False,
            },
            "max_actions": 12,
            "timeout_seconds": 60,
            "acceptance": {"visible_text": "Received!"},
        }
    )


def test_policy_allows_safe_semantic_click() -> None:
    decision = validate_action(
        task(),
        RestrictedBrowserAction(type="click", target=ActionTarget(role="button", name="Next")),
    )

    assert decision.allowed is True


def test_real_amazon_search_is_authorized_but_other_submits_are_not() -> None:
    amazon = load_task(
        Path(__file__).parents[1] / "tasks/experimental/amazon-cheapest-coffee-beans-en.yaml"
    )
    for label, allowed in [("Buscar Amazon.es", True), ("Password", False), ("Comprar", False)]:
        action = RestrictedBrowserAction(
            type="press", target=ActionTarget(role="textbox", placeholder=label), value="ENTER"
        )
        assert validate_action(amazon, action).allowed is allowed


def test_policy_denies_navigation_outside_task_allowlist() -> None:
    decision = validate_action(
        task(), RestrictedBrowserAction(type="navigate", value="https://example.com")
    )

    assert decision.allowed is False
    assert decision.reason == "domain_not_allowed"


def test_policy_denies_submit_and_enter_without_authority() -> None:
    click = validate_action(
        task(),
        RestrictedBrowserAction(type="click", target=ActionTarget(role="button", name="Submit")),
    )
    press = validate_action(
        task(),
        RestrictedBrowserAction(
            type="press", target=ActionTarget(role="textbox", name="Name"), value="Enter"
        ),
    )

    assert click.allowed is False
    assert click.reason == "form_submit_not_allowed"
    assert press.allowed is False
    assert press.reason == "form_submit_not_allowed"


def test_policy_allows_explicit_read_only_search_submit() -> None:
    wikipedia_task = TaskSpec.model_validate(
        {
            "schema_version": 1,
            "id": "wikipedia-search",
            "start_url": "https://www.wikipedia.org/",
            "instruction": "Busca Playwright y abre el artículo principal.",
            "completion": "La página final muestra el artículo solicitado.",
            "policy": {
                "allowed_domains": ["www.wikipedia.org", "en.wikipedia.org"],
                "risk": "read_only",
                "allowed_submit_labels": ["Search Wikipedia"],
            },
            "max_actions": 12,
            "timeout_seconds": 60,
            "acceptance": {"page_title": "Playwright"},
        }
    )

    decision = validate_action(
        wikipedia_task,
        RestrictedBrowserAction(type="press", target={"label": "Search Wikipedia"}, value="Enter"),
    )

    assert decision.allowed


def test_policy_allows_search_submit_when_authorized_by_name_or_placeholder() -> None:
    wikipedia_task = TaskSpec.model_validate(
        {
            "schema_version": 1,
            "id": "wikipedia-search",
            "start_url": "https://www.wikipedia.org/",
            "instruction": "Busca Playwright y abre el artículo principal.",
            "completion": "La página final muestra el artículo solicitado.",
            "policy": {
                "allowed_domains": ["www.wikipedia.org", "en.wikipedia.org"],
                "risk": "read_only",
                "allowed_submit_labels": ["Search Wikipedia"],
            },
            "max_actions": 12,
            "timeout_seconds": 60,
            "acceptance": {"page_title": "Playwright"},
        }
    )

    for target in (
        {"role": "searchbox", "name": "Search Wikipedia"},
        {"role": "searchbox", "placeholder": "Search Wikipedia"},
    ):
        decision = validate_action(
            wikipedia_task,
            RestrictedBrowserAction(type="press", target=target, value="ENTER"),
        )
        assert decision.allowed


def test_policy_allows_enter_on_a_semantic_searchbox_without_submit_authority() -> None:
    search_task = TaskSpec.model_validate(
        {
            "schema_version": 1,
            "id": "amazon-search",
            "start_url": "https://www.amazon.es/",
            "instruction": "Busca café en grano y termina.",
            "completion": "La búsqueda está visible.",
            "policy": {"allowed_domains": ["www.amazon.es"], "risk": "read_only"},
            "max_actions": 12,
            "timeout_seconds": 60,
            "acceptance": {"url_contains": "amazon.es"},
        }
    )

    decision = validate_action(
        search_task,
        RestrictedBrowserAction(
            type="press", target={"role": "searchbox", "name": "Search Amazon.es"}, value="Enter"
        ),
    )

    assert decision.allowed


def test_policy_keeps_other_read_only_submits_denied() -> None:
    wikipedia_task = TaskSpec.model_validate(
        {
            "schema_version": 1,
            "id": "wikipedia-search",
            "start_url": "https://www.wikipedia.org/",
            "instruction": "Busca Playwright y abre el artículo principal.",
            "completion": "La página final muestra el artículo solicitado.",
            "policy": {"allowed_domains": ["www.wikipedia.org"], "risk": "read_only"},
            "max_actions": 12,
            "timeout_seconds": 60,
            "acceptance": {"page_title": "Playwright"},
        }
    )

    decision = validate_action(
        wikipedia_task,
        RestrictedBrowserAction(type="press", target={"label": "Search Wikipedia"}, value="Enter"),
    )

    assert not decision.allowed
