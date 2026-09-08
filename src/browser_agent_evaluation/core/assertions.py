from __future__ import annotations

from dataclasses import dataclass, field

from browser_agent_evaluation.core.models import AcceptanceSpec
from browser_agent_evaluation.core.open_verification import verify_open


@dataclass(frozen=True)
class PageState:
    url: str
    title: str
    visible_text: str
    input_values: dict[str, str]
    facts: dict[str, str] = field(default_factory=dict)
    answer: str = ""


def evaluate_acceptance(acceptance: AcceptanceSpec, state: PageState) -> dict[str, bool]:
    results: dict[str, bool] = {}
    if acceptance.verifier:
        results.update(verify_open(acceptance.verifier, state.facts, state.answer))
    if acceptance.page_title is not None:
        results["page_title"] = acceptance.page_title.casefold() in state.title.casefold()
    if acceptance.url_contains is not None:
        results["url_contains"] = acceptance.url_contains.casefold() in state.url.casefold()
    if acceptance.visible_text is not None:
        expected_text = acceptance.visible_text.casefold()
        results["visible_text"] = expected_text in state.visible_text.casefold()
    if acceptance.input_value is not None:
        results["input_value"] = acceptance.input_value in state.input_values.values()
    return results
