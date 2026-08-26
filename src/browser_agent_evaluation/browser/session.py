from __future__ import annotations

from browser_agent_evaluation.browser.playwright import (
    LivePlaywrightController,
    restrict_page_network,
)
from browser_agent_evaluation.core.models import TaskSpec


async def new_controller(
    browser: object,
    task: TaskSpec,
    *,
    restrict_network: bool = True,
    viewport: dict[str, int] | None = None,
) -> tuple[LivePlaywrightController, object]:
    context_options = {"viewport": viewport} if viewport is not None else {}
    context = await browser.new_context(**context_options)  # type: ignore[attr-defined]
    page = await context.new_page()
    if restrict_network:
        await restrict_page_network(page, allowed_domains=task.policy.allowed_domains)
    return LivePlaywrightController(page, allowed_domains=task.policy.allowed_domains), context
