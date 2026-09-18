"""Declarative modal screens prepared from document markup."""
from __future__ import annotations

from collections.abc import Iterable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widget import Widget

from ..registry import AttributeSpec, BuildContext, ComponentRegistry, ComponentSpec, boolean


class MarkupModal(ModalScreen[object]):
    """A modal screen whose contents come from a TextUI node tree."""

    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    def __init__(self, children: Iterable[Widget], *, dismissable: bool) -> None:
        super().__init__()
        self._children = tuple(children)
        self.dismissable = dismissable

    def compose(self) -> ComposeResult:
        yield from self._children

    def action_cancel(self) -> None:
        if self.dismissable:
            self.dismiss(None)


def build_modal(context: BuildContext) -> MarkupModal:
    return MarkupModal(context.children, dismissable=context.attributes["dismissable"])


def register_modal(registry: ComponentRegistry) -> None:
    registry.register(ComponentSpec(
        tag="modal",
        factory=build_modal,
        child_policy="widgets",
        attributes={"dismissable": AttributeSpec(boolean, default=True)},
    ))
