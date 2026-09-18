"""Native select, switch, and text area component adapters."""
from __future__ import annotations

from textual.content import Content
from textual.widget import Widget
from textual.widgets import Select, Switch, TextArea

from ..registry import AttributeSpec, BuildContext, ComponentRegistry, ComponentSpec, EventSpec, boolean, enum


class SelectOption(Widget):
    """A parsed option value consumed by the select factory, never mounted."""

    def __init__(self, label: str, value: str) -> None:
        super().__init__()
        self.label = label
        self.value = value


def build_option(context: BuildContext) -> SelectOption:
    return SelectOption(context.text or "", context.attributes["value"])


def build_select(context: BuildContext) -> Select[str]:
    options = [(Content(option.label), option.value) for option in context.children]
    value = context.attributes.get("value", Select.NULL)
    if value is Select.NULL and not context.attributes["allow-blank"]:
        value = context.children[0].value
    return Select(
        options,
        prompt=context.attributes["prompt"],
        allow_blank=context.attributes["allow-blank"],
        value=value,
    )


def build_switch(context: BuildContext) -> Switch:
    return Switch(value=context.attributes["value"])


def build_text_area(context: BuildContext) -> TextArea:
    return TextArea(
        context.text or "",
        language=context.attributes.get("language"),
        soft_wrap=context.attributes["soft-wrap"],
        read_only=context.attributes["read-only"],
        show_line_numbers=context.attributes["show-line-numbers"],
        tab_behavior=context.attributes["tab-behavior"],
        placeholder=context.attributes["placeholder"],
    )


def register_form_controls(registry: ComponentRegistry) -> None:
    registry.register(ComponentSpec(
        tag="option", factory=build_option, text_policy="text",
        attributes={"value": AttributeSpec(required=True)},
    ))
    registry.register(ComponentSpec(
        tag="select", factory=build_select, child_policy="widgets",
        attributes={
            "value": AttributeSpec(),
            "prompt": AttributeSpec(default="Select"),
            "allow-blank": AttributeSpec(boolean, default=True),
        },
        events={"changed": EventSpec(Select.Changed, lambda event: event.select)},
    ))
    registry.register(ComponentSpec(
        tag="switch", factory=build_switch,
        attributes={"value": AttributeSpec(boolean, default=False)},
        events={"changed": EventSpec(Switch.Changed, lambda event: event.switch)},
    ))
    registry.register(ComponentSpec(
        tag="text-area", factory=build_text_area, text_policy="verbatim",
        attributes={
            "language": AttributeSpec(),
            "soft-wrap": AttributeSpec(boolean, default=True),
            "read-only": AttributeSpec(boolean, default=False),
            "show-line-numbers": AttributeSpec(boolean, default=False),
            "tab-behavior": AttributeSpec(enum("focus", "indent"), default="focus"),
            "placeholder": AttributeSpec(default=""),
        },
        events={"changed": EventSpec(TextArea.Changed, lambda event: event.text_area)},
    ))
