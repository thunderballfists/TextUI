"""Declarative modal screens prepared from document markup."""
from __future__ import annotations

from collections.abc import Callable, Iterable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widget import Widget

from ..registry import AttributeSpec, BuildContext, ComponentRegistry, ComponentSpec, boolean


class MarkupModal(ModalScreen[object]):
    """A modal screen whose contents come from a TextUI node tree."""

    DEFAULT_CSS = """
    MarkupModal {
        align: center middle;
    }
    MarkupModal > .markup-modal-content {
        width: auto;
        min-width: 28;
        height: auto;
        max-width: 80%;
        max-height: 80%;
        overflow-y: auto;
        padding: 1 2;
        border: round $primary;
        background: $surface;
        align: center middle;
    }
    MarkupModal > .markup-modal-content > Button {
        width: 100%;
    }
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    def __init__(self, children: Iterable[Widget], *, dismissable: bool) -> None:
        super().__init__()
        self._children = tuple(children)
        self.dismissable = dismissable
        self._dismissal_value: object | None = None
        self._on_unmount_callback: Callable[[object | None], None] | None = None

    def compose(self) -> ComposeResult:
        yield Vertical(*self._children, classes="markup-modal-content")

    def action_cancel(self) -> None:
        if self.dismissable:
            self.dismiss(None)

    def set_dismissal_value(self, value: object | None) -> None:
        """Retain the value supplied by Textual's screen-dismiss callback."""
        self._dismissal_value = value

    def set_unmount_callback(self, callback: Callable[[object | None], None]) -> None:
        """Register one owner cleanup callback for this screen's removal."""
        self._on_unmount_callback = callback

    def on_unmount(self) -> None:
        """Release document-owned state after normal dismissal or app shutdown."""
        callback, self._on_unmount_callback = self._on_unmount_callback, None
        if callback is not None:
            callback(self._dismissal_value)


def build_modal(context: BuildContext) -> MarkupModal:
    return MarkupModal(context.children, dismissable=context.attributes["dismissable"])


def register_modal(registry: ComponentRegistry) -> None:
    registry.register(ComponentSpec(
        tag="modal",
        factory=build_modal,
        child_policy="widgets",
        attributes={"dismissable": AttributeSpec(boolean, default=True)},
    ))
