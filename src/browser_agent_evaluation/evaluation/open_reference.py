from __future__ import annotations

import json
from urllib.parse import urljoin, urlsplit

from browser_agent_evaluation.agents.reference import ReferenceResult
from browser_agent_evaluation.browser.playwright import LivePlaywrightController
from browser_agent_evaluation.core.models import TaskSpec
from browser_agent_evaluation.core.open_verification import unit_price, verify_open


async def run_open_reference(
    controller: LivePlaywrightController,
    task: TaskSpec,
) -> tuple[ReferenceResult, dict[str, str]]:
    """Discover links on the live site, then apply the same independent verifier."""
    page = controller._page
    await controller.navigate(task.start_url)
    actions = 1
    if task.acceptance.verifier == "amazon_coffee_under_14":
        await controller.navigate("https://www.amazon.es/s?k=cafe+en+grano")
        actions += 1
        selector = (
            '[data-component-type="s-search-result"] h2 a, '
            '[data-component-type="s-search-result"] a:has(h2)'
        )
    else:
        selector = 'a[href*="/futbol/real-madrid/"][href*=".html"]'
    links = await page.locator(selector).evaluate_all("els => els.map(e => e.href)")
    facts: dict[str, str] = {}
    checks: dict[str, bool] = {"candidate_found": False}
    for link in list(dict.fromkeys(links))[: min(12, task.max_actions - actions)]:
        url = urljoin(task.start_url, link)
        if urlsplit(url).hostname not in task.policy.allowed_domains:
            continue
        await controller.navigate(url)
        actions += 1
        facts = await controller.verification_facts()
        answer: dict[str, object] = {"name": facts.get("heading", ""), "url": facts.get("url", "")}
        if task.acceptance.verifier == "amazon_coffee_under_14":
            price = unit_price(facts.get("price_text", ""))
            answer["eur_per_kg"] = str(price) if price is not None else None
        facts["answer"] = json.dumps(answer, ensure_ascii=False)
        checks = verify_open(task.acceptance.verifier or "", facts, facts["answer"])
        if all(checks.values()):
            return ReferenceResult(True, checks, actions, "accepted"), facts
    return ReferenceResult(False, checks, actions, "acceptance_failed"), facts
