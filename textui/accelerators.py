"""Document-scoped tab accelerators."""
from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from textual.app import App
from textual.screen import Screen
from textual.widgets import TabbedContent, TabPane

from .nodes import ElementNode

if TYPE_CHECKING:
    from .document import BoundDocument


def _walk(nodes: Iterable[ElementNode]) -> Iterable[ElementNode]:
    for node in nodes:
        yield node
        yield from _walk(node.children)


def tab_accelerators(nodes: Iterable[ElementNode]) -> tuple[tuple[str, str], ...]:
    return tuple(
        (node.attributes["accelerator"], node.common["id"])
        for node in _walk(nodes)
        if node.spec.tag == "tab-pane" and "accelerator" in node.attributes
    )


def install_tab_accelerators(host: App | Screen, nodes: Iterable[ElementNode]) -> None:
    """Install bindings on their host; dormant modals own separate bindings."""
    nodes = tuple(node for node in nodes if node.spec.tag != "modal")
    for key, pane_id in tab_accelerators(nodes):
        action = f"textui_activate_tab('{pane_id}')"
        if isinstance(host, App):
            host.bind(key, action, show=False)
        else:
            # Native modal binding chains stop at the screen, so target the App.
            host._bindings.bind(key, f"app.{action}", show=False)


def tab_available(document: BoundDocument | None, pane_id: str) -> bool:
    if document is None:
        return False
    pane = document._get_mounted_widget(pane_id)
    return isinstance(pane, TabPane) and pane.screen is document.app.screen


def activate_tab(document: BoundDocument, pane_id: str) -> None:
    if not tab_available(document, pane_id):
        return
    pane = document._get_mounted_widget(pane_id)
    assert pane is not None
    parent = pane.parent
    while parent is not None and not isinstance(parent, TabbedContent):
        parent = parent.parent
    if parent is None:
        raise RuntimeError(f"tab pane {pane_id!r} is not mounted in tabbed content")
    parent.active = pane_id
    parent.focus()
