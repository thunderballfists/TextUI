"""Native static tabbed content adapters."""
from __future__ import annotations

from textual.content import Content
from textual.widgets import TabbedContent, TabPane

from ..registry import AttributeSpec, BuildContext, ComponentRegistry, ComponentSpec, EventSpec, enum


class DocumentTabbedContent(TabbedContent):
    """Native tabs with shell layout defaults independent of the host App."""

    DEFAULT_CSS = """
    DocumentTabbedContent { height: 1fr; }
    DocumentTabbedContent > ContentSwitcher { height: 1fr; }
    """


class DocumentTabPane(TabPane):
    """Fill the document tabs unless author TCSS requests another height."""

    DEFAULT_CSS = "DocumentTabPane { height: 1fr; }"


def accelerator(value: str) -> str:
    if len(value) != 1 or not value.isalnum():
        raise ValueError("accelerator must be one alphanumeric character")
    return value


def build_tab_pane(context: BuildContext) -> TabPane:
    return DocumentTabPane(Content(context.attributes["title"]), *context.children)


def build_tabbed_content(context: BuildContext) -> TabbedContent:
    tabs = DocumentTabbedContent(initial=context.attributes.get("initial", ""))
    for pane in context.children:
        tabs.compose_add_child(pane)
    return tabs


def register_tabs(registry: ComponentRegistry) -> None:
    registry.register(ComponentSpec(
        tag="tab-pane", factory=build_tab_pane, child_policy="widgets",
        attributes={
            "title": AttributeSpec(required=True),
            "accelerator": AttributeSpec(accelerator),
            "accelerator-scope": AttributeSpec(enum("document")),
        },
    ))
    registry.register(ComponentSpec(
        tag="tabbed-content", factory=build_tabbed_content, child_policy="widgets",
        attributes={"initial": AttributeSpec()},
        events={"tab-activated": EventSpec(TabbedContent.TabActivated, lambda event: event.tabbed_content)},
    ))
