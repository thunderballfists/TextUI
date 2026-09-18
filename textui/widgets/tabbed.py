"""Native static tabbed content adapters."""
from __future__ import annotations

from textual.content import Content
from textual.widgets import TabbedContent, TabPane

from ..registry import AttributeSpec, BuildContext, ComponentRegistry, ComponentSpec, EventSpec


def build_tab_pane(context: BuildContext) -> TabPane:
    return TabPane(Content(context.attributes["title"]), *context.children)


def build_tabbed_content(context: BuildContext) -> TabbedContent:
    tabs = TabbedContent(initial=context.attributes.get("initial", ""))
    for pane in context.children:
        tabs.compose_add_child(pane)
    return tabs


def register_tabs(registry: ComponentRegistry) -> None:
    registry.register(ComponentSpec(
        tag="tab-pane", factory=build_tab_pane, child_policy="widgets",
        attributes={"title": AttributeSpec(required=True)},
    ))
    registry.register(ComponentSpec(
        tag="tabbed-content", factory=build_tabbed_content, child_policy="widgets",
        attributes={"initial": AttributeSpec()},
        events={"tab-activated": EventSpec(TabbedContent.TabActivated, lambda event: event.tabbed_content)},
    ))
