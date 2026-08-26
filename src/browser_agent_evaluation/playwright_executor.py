from __future__ import annotations

from typing import Protocol

from browser_agent_evaluation.models import ActionTarget, RestrictedBrowserAction


class BrowserController(Protocol):
    async def observe(self) -> str: ...
    async def click(self, target: ActionTarget) -> None: ...
    async def fill(self, target: ActionTarget, value: str) -> None: ...
    async def select(self, target: ActionTarget, value: str) -> None: ...
    async def check(self, target: ActionTarget) -> None: ...
    async def press(self, target: ActionTarget, value: str) -> None: ...
    async def wait(self) -> None: ...
    async def extract_text(self, target: ActionTarget) -> str: ...
    async def navigate(self, url: str) -> None: ...


async def execute_action(browser: BrowserController, action: RestrictedBrowserAction) -> str | None:
    if action.type == "navigate":
        await browser.navigate(action.value or "")
        return None
    if action.type == "wait":
        await browser.wait()
        return None
    target = action.target
    if target is None:
        raise ValueError(f"{action.type} requires a target")
    if action.type == "click":
        await browser.click(target)
    elif action.type == "fill":
        await browser.fill(target, action.value or "")
    elif action.type == "select":
        await browser.select(target, action.value or "")
    elif action.type == "check":
        await browser.check(target)
    elif action.type == "press":
        await browser.press(target, action.value or "")
    elif action.type == "extract_text":
        return await browser.extract_text(target)
    else:
        raise ValueError(f"unsupported action: {action.type}")
    return None
