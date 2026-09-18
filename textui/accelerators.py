"""Document-scoped tab accelerators."""
from __future__ import annotations

from collections.abc import Iterable

from textual.app import App
from textual.widgets import TabbedContent

from .nodes import ElementNode


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


def install_tab_accelerators(app: App, nodes: Iterable[ElementNode]) -> None:
    for key, pane_id in tab_accelerators(nodes):
        app.bind(key, f"textui_activate_tab('{pane_id}')", show=False)


def activate_tab(document, pane_id: str) -> None:
    pane = document.get_by_id(pane_id)
    parent = pane.parent
    while parent is not None and not isinstance(parent, TabbedContent):
        parent = parent.parent
    if parent is None:
        raise RuntimeError(f"tab pane {pane_id!r} is not mounted in tabbed content")
    parent.active = pane_id
    parent.focus()
