from __future__ import annotations

from browser_agent_evaluation.assertions import PageState, evaluate_acceptance
from browser_agent_evaluation.models import AcceptanceSpec


def test_acceptance_requires_all_declared_conditions() -> None:
    result = evaluate_acceptance(
        AcceptanceSpec(
            page_title="Playwright",
            url_contains="Playwright",
            visible_text="Browser automation",
        ),
        PageState(
            url="https://en.wikipedia.org/wiki/Playwright",
            title="Playwright - Wikipedia",
            visible_text="Playwright is a browser automation library.",
            input_values={},
        ),
    )

    assert result == {"page_title": True, "url_contains": True, "visible_text": True}


def test_wikipedia_acceptance_rejects_search_results_page() -> None:
    result = evaluate_acceptance(
        AcceptanceSpec(page_title="Playwright", url_contains="/wiki/Playwright"),
        PageState(
            url=(
                "https://en.wikipedia.org/w/index.php?search=Playwright&"
                "title=Special%3ASearch"
            ),
            title="Playwright - Search results - Wikipedia",
            visible_text="Playwright search results",
            input_values={},
        ),
    )

    assert result == {"page_title": True, "url_contains": False}


def test_acceptance_detects_runner_claim_that_does_not_match_page_state() -> None:
    result = evaluate_acceptance(
        AcceptanceSpec(page_title="Playwright", input_value="Ada Lovelace"),
        PageState(
            url="https://example.test/",
            title="Wikipedia",
            visible_text="",
            input_values={"name": "Grace Hopper"},
        ),
    )

    assert result == {"page_title": False, "input_value": False}
