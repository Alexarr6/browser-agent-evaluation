from __future__ import annotations

import asyncio
from typing import Any

from browser_agent_evaluation.live_playwright import LivePlaywrightController
from browser_agent_evaluation.models import ActionTarget


class FakeLocator:
    def __init__(self, selected: list[str]) -> None:
        self.selected = selected

    def or_(self, other: FakeLocator) -> FakeLocator:
        return self

    def filter(self, *, has: FakeLocator) -> FakeLocator:
        return self

    async def select_option(self, *, label: str) -> None:
        self.selected.append(label)


class FakePage:
    def __init__(self) -> None:
        self.roles: list[tuple[str, str | None]] = []
        self.labels: list[str] = []
        self.selected: list[str] = []

    def get_by_label(self, name: str, *, exact: bool) -> FakeLocator:
        assert exact is True
        self.labels.append(name)
        return FakeLocator(self.selected)

    def get_by_role(
        self, role: Any, *, name: str | None = None, exact: bool = False
    ) -> FakeLocator:
        if name is not None:
            assert exact is True
        self.roles.append((str(role), name))
        return FakeLocator(self.selected)


def test_text_target_selects_the_combobox_containing_that_option() -> None:
    page = FakePage()
    controller = LivePlaywrightController(page, allowed_domains=["example.test"])  # type: ignore[arg-type]

    asyncio.run(controller.select(ActionTarget(text="Two"), "ignored"))

    assert page.selected == ["Two"]
    assert page.roles == [("option", "Two"), ("combobox", None)]


def test_name_only_target_uses_bounded_semantic_role_fallbacks() -> None:
    page = FakePage()
    controller = LivePlaywrightController(page, allowed_domains=["example.test"])  # type: ignore[arg-type]

    asyncio.run(controller._locator(ActionTarget(name="Submit")))

    assert page.labels == ["Submit"]
    assert page.roles == [
        ("button", "Submit"),
        ("textbox", "Submit"),
        ("combobox", "Submit"),
        ("checkbox", "Submit"),
        ("radio", "Submit"),
        ("link", "Submit"),
    ]


class ResolvingLocator:
    def __init__(self, *, count: int, visible: bool = True) -> None:
        self._count = count
        self._visible = visible

    async def count(self) -> int:
        return self._count

    def nth(self, _: int) -> ResolvingLocator:
        return self

    async def is_visible(self) -> bool:
        return self._visible

    @property
    def first(self) -> ResolvingLocator:
        return self


class ResolvingPage(FakePage):
    def get_by_label(self, name: str, *, exact: bool) -> ResolvingLocator:
        self.labels.append(name)
        return ResolvingLocator(count=0)

    def get_by_role(
        self, role: Any, *, name: str | None = None, exact: bool = False
    ) -> ResolvingLocator:
        self.roles.append((str(role), name))
        if str(role) == "textbox" and name is None:
            return ResolvingLocator(count=1)
        return ResolvingLocator(count=0)


def test_role_name_falls_back_to_role_when_accessible_name_is_wrong() -> None:
    page = ResolvingPage()
    controller = LivePlaywrightController(page, allowed_domains=["example.test"])

    locator = asyncio.run(
        controller._locator(ActionTarget(role="textbox", name="New label text"))
    )

    assert isinstance(locator, ResolvingLocator)
    assert page.roles[:2] == [("textbox", "New label text"), ("textbox", None)]


def test_unmatched_label_uses_action_role_hint_for_a_single_control() -> None:
    page = ResolvingPage()
    controller = LivePlaywrightController(page, allowed_domains=["example.test"])

    locator = asyncio.run(
        controller._locator(ActionTarget(label="New label text"), role_hint="textbox")
    )

    assert isinstance(locator, ResolvingLocator)
    assert page.roles == [("textbox", None)]
