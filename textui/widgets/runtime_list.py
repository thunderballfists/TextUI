"""A runtime-populated list with native Textual selection behavior."""
from __future__ import annotations

import asyncio
from collections.abc import Iterable, Mapping
from types import MappingProxyType

from textual import events
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, ListItem, ListView
from textual.content import Content

from ..registry import AttributeSpec, BuildContext, ComponentRegistry, ComponentSpec, EventSpec


class RuntimeListItem(ListItem):
    """A native list row that retains the mapping which rendered it."""

    class Activated(Message):
        def __init__(self, item: RuntimeListItem) -> None:
            super().__init__()
            self.item = item

    def __init__(self, item: Mapping[str, object], label: str) -> None:
        super().__init__(Label(Content(label), markup=False))
        self.item = MappingProxyType(dict(item))

    def _on_click(self, _: events.Click) -> None:
        self.post_message(self.Activated(self))


class RuntimeList(ListView):
    """A ListView populated from mappings supplied by controller code."""

    selected: reactive[Mapping[str, object] | None] = reactive(None, init=False)

    class ItemSelected(Message):
        """Posted after a row is selected by mouse or keyboard."""

        def __init__(self, list_view: RuntimeList, item: Mapping[str, object], index: int) -> None:
            super().__init__()
            self.list_view = list_view
            self.item = item
            self.index = index

    def __init__(self, *, item_label: str) -> None:
        super().__init__(initial_index=None)
        self.item_label = item_label
        self.items: tuple[RuntimeListItem, ...] = ()
        self._set_items_lock = asyncio.Lock()

    async def set_items(self, items: Iterable[Mapping[str, object]]) -> None:
        """Replace rows with mappings and render each `item-label` pattern."""
        async with self._set_items_lock:
            rendered = tuple(self._make_item(item) for item in items)
            self.items = rendered
            self.selected = None
            self.index = None
            await self.remove_children()
            await self.mount(*rendered)
            if rendered:
                self.index = 0

    def _make_item(self, item: Mapping[str, object]) -> RuntimeListItem:
        if not isinstance(item, Mapping):
            raise TypeError("list items must be mappings")
        try:
            label = self.item_label.format_map(item)
        except (KeyError, ValueError) as error:
            raise ValueError(f"item-label cannot format item: {error}") from error
        return RuntimeListItem(item, label)

    def action_select_cursor(self) -> None:
        item = self.highlighted_child
        if isinstance(item, RuntimeListItem) and self.index is not None:
            self._select(item, self.index)

    def on_runtime_list_item_activated(self, event: RuntimeListItem.Activated) -> None:
        event.stop()
        self.focus()
        index = self._nodes.index(event.item)
        self.index = index
        self._select(event.item, index)

    def _select(self, item: RuntimeListItem, index: int) -> None:
        self.selected = item.item
        self.post_message(self.ItemSelected(self, item.item, index))


def _list_source(event: RuntimeList.ItemSelected) -> RuntimeList:
    return event.list_view


def nonempty_string(value: str) -> str:
    if not value:
        raise ValueError("expected a nonempty value")
    return value


def build_runtime_list(context: BuildContext) -> RuntimeList:
    return RuntimeList(item_label=context.attributes["item-label"])


def register_runtime_list(registry: ComponentRegistry) -> None:
    registry.register(ComponentSpec(
        tag="list",
        factory=build_runtime_list,
        attributes={"item-label": AttributeSpec(nonempty_string, required=True)},
        events={"selected": EventSpec(RuntimeList.ItemSelected, _list_source)},
    ))
