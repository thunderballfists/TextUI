"""A small native navigation list with explicit content targets."""
from __future__ import annotations

from collections.abc import Iterable

from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Button

from ..errors import DocumentValidationError
from ..nodes import ElementNode


class NavItem(Button):
    DEFAULT_CSS = "NavItem { width: 100%; } NavItem.-selected { text-style: bold; }"

    def __init__(self, label: str, *, target: str) -> None:
        super().__init__(label)
        self.target = target


class Nav(Vertical):
    DEFAULT_CSS = "Nav { width: 100%; height: 100%; }"

    class Selected(Message):
        def __init__(self, nav: Nav, target: str) -> None:
            super().__init__()
            self.nav = nav
            self.target = target

    def __init__(self, *items: NavItem) -> None:
        super().__init__(*items)
        self.items = items
        self.selected: str | None = None

    def on_mount(self) -> None:
        if self.items:
            self.selected = self.items[0].target
            self.items[0].add_class("-selected")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        item = event.button
        if item not in self.items:
            return
        for candidate in self.items:
            candidate.set_class(candidate is item, "-selected")
        self.selected = item.target
        self.post_message(self.Selected(self, item.target))


def validate_navigation_targets(nodes: Iterable[ElementNode]) -> None:
    def walk(items: Iterable[ElementNode]):
        for node in items:
            yield node
            yield from walk(node.children)

    all_nodes = tuple(walk(nodes))
    targets = {
        child.common["id"]
        for node in all_nodes if node.spec.tag == "content-switcher"
        for child in node.children if child.common["id"] is not None
    }
    for node in all_nodes:
        if node.spec.tag == "nav-item" and node.attributes["target"] not in targets:
            raise DocumentValidationError(
                f"navigation target {node.attributes['target']!r} is not a content-switcher child",
                location=node.location, attribute="target",
            )
        if node.spec.tag == "content-switcher" and node.attributes.get("initial") not in {None, *(child.common["id"] for child in node.children)}:
            raise DocumentValidationError("initial content target is not a child", location=node.location, attribute="initial")
