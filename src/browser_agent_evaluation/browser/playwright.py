from __future__ import annotations

from typing import Any, cast
from urllib.parse import urlparse

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Locator, Page, Route

from browser_agent_evaluation.browser.executor import execute_action
from browser_agent_evaluation.core.assertions import PageState
from browser_agent_evaluation.core.models import ActionTarget, RestrictedBrowserAction


class LiveBrowserPolicyError(RuntimeError):
    """Raised when a live page action would leave its task's domain policy."""


class LivePlaywrightController:
    def __init__(self, page: Page, *, allowed_domains: list[str]) -> None:
        self._page = page
        self._allowed_domains = frozenset(allowed_domains)

    async def observe(self) -> str:
        body = self._page.locator("body")
        visible_text = await body.inner_text()
        try:
            accessibility_tree = await body.aria_snapshot()
        except PlaywrightError:
            accessibility_tree = ""
        parts = [f"URL: {self._page.url}", f"Visible text:\n{visible_text}"]
        if accessibility_tree:
            parts.append(f"Accessibility tree:\n{accessibility_tree}")
        return "\n\n".join(parts)[:20_000]

    async def click(self, target: ActionTarget) -> None:
        await (await self._locator(target, role_hint="button")).click()
        self._ensure_current_domain()

    async def fill(self, target: ActionTarget, value: str) -> None:
        await (await self._locator(target, role_hint="textbox")).fill(value)

    async def select(self, target: ActionTarget, value: str) -> None:
        if target.text:
            option = self._page.get_by_role("option", name=target.text, exact=True)
            combobox = self._page.get_by_role("combobox").filter(has=option)
            try:
                if await combobox.count() > 0:
                    await combobox.first.select_option(label=target.text)
                    return
            except AttributeError:
                # Keep lightweight controller fakes compatible with this branch.
                await combobox.select_option(label=target.text)
                return
        locator = await self._locator(target, role_hint="combobox")
        try:
            await locator.select_option(label=value)
        except PlaywrightError:
            # Models naturally report the visible option label (for example, "Two"),
            # while HTML select_option may require the underlying value (for example, "2").
            await locator.select_option(value=value)

    async def check(self, target: ActionTarget) -> None:
        await (await self._locator(target)).check()

    async def press(self, target: ActionTarget, value: str) -> None:
        await (await self._locator(target, role_hint="textbox")).press(value)
        self._ensure_current_domain()

    async def wait(self) -> None:
        await self._page.wait_for_timeout(6_000)

    async def extract_text(self, target: ActionTarget) -> str:
        return await (await self._locator(target)).inner_text()

    async def navigate(self, url: str) -> None:
        self._ensure_allowed_url(url)
        await self._page.goto(url, wait_until="domcontentloaded")
        self._ensure_current_domain()

    async def page_state(self) -> PageState:
        return PageState(
            url=self._page.url,
            title=await self._page.title(),
            visible_text=await self.observe(),
            input_values={},
        )

    async def _locator(self, target: ActionTarget, *, role_hint: str | None = None) -> Locator:
        candidates: list[Locator] = []

        def add(candidate: Locator) -> None:
            candidates.append(candidate)

        if target.role and target.name:
            add(self._page.get_by_role(cast(Any, target.role), name=target.name, exact=True))
        if target.role and target.text:
            add(self._page.get_by_role(cast(Any, target.role), name=target.text, exact=True))
        if target.label:
            add(self._page.get_by_label(target.label, exact=True))
        if target.placeholder:
            add(self._page.get_by_placeholder(target.placeholder, exact=True))
        if target.text:
            add(self._page.get_by_text(target.text, exact=True))
        if target.role:
            add(self._page.get_by_role(cast(Any, target.role)))
        if target.name:
            add(self._page.get_by_label(target.name, exact=True))
            for role in ("button", "textbox", "combobox", "checkbox", "radio", "link"):
                add(self._page.get_by_role(cast(Any, role), name=target.name, exact=True))
        if role_hint and not target.role:
            add(self._page.get_by_role(cast(Any, role_hint)))

        if not candidates:
            raise LiveBrowserPolicyError("semantic target is required")
        return await self._first_visible_candidate(candidates)

    @staticmethod
    async def _first_visible_candidate(candidates: list[Locator]) -> Locator:
        fallback: Locator | None = None
        for candidate in candidates:
            try:
                count = await candidate.count()
            except AttributeError:
                # Unit-test fakes and older adapters may only implement the action API.
                return candidate
            if count == 0:
                continue
            fallback = candidate
            for index in range(count):
                item = candidate.nth(index)
                try:
                    if await item.is_visible():
                        return item
                except PlaywrightError:
                    continue
        if fallback is not None:
            return fallback.first
        raise LiveBrowserPolicyError("semantic target did not match any page element")

    def _ensure_allowed_url(self, url: str) -> None:
        if urlparse(url).hostname not in self._allowed_domains:
            raise LiveBrowserPolicyError("URL is outside allowed domains")

    def _ensure_current_domain(self) -> None:
        self._ensure_allowed_url(self._page.url)


class LiveReferenceExecutor:
    def __init__(self, controller: LivePlaywrightController) -> None:
        self._controller = controller

    async def execute(self, action: RestrictedBrowserAction) -> None:
        await execute_action(self._controller, action)

    async def page_state(self) -> PageState:
        return await self._controller.page_state()


async def restrict_page_network(page: Page, *, allowed_domains: list[str]) -> None:
    allowed_hosts = frozenset(allowed_domains)

    async def route_request(route: Route) -> None:
        url = route.request.url
        parsed = urlparse(url)
        if parsed.scheme in {"about", "data"} or parsed.hostname in allowed_hosts:
            await route.continue_()
        else:
            await route.abort()

    await page.route("**/*", route_request)
