"""The six deliberately small native Textual component adapters."""
from __future__ import annotations

from textual.containers import Horizontal, Vertical
from textual.content import Content
from textual.widgets import Button, Checkbox, Input, Label
from .split import Pane, Split

from ..registry import (
    AttributeSpec,
    BuildContext,
    ComponentRegistry,
    ComponentSpec,
    EventSpec,
    boolean,
    enum,
    integer,
)


def build_vertical(context: BuildContext) -> Vertical:
    return Vertical(*context.children)


def build_horizontal(context: BuildContext) -> Horizontal:
    return Horizontal(*context.children)


def build_label(context: BuildContext) -> Label:
    return Label(Content(context.text or ""), markup=False)


def build_button(context: BuildContext) -> Button:
    return Button(Content(context.text or ""), variant=context.attributes["variant"])


def build_input(context: BuildContext) -> Input:
    options = dict(context.attributes)
    if "max-length" in options:
        options["max_length"] = options.pop("max-length")
    return Input(**options)


def build_checkbox(context: BuildContext) -> Checkbox:
    return Checkbox(Content(context.text or ""), value=context.attributes["value"])


def build_pane(context: BuildContext) -> Pane:
    return Pane(*context.children, min_size=context.attributes["min-size"], size=context.attributes.get("size"))


def build_split(context: BuildContext) -> Split:
    if len(context.children) != 2 or any(not isinstance(child, Pane) for child in context.children):
        raise ValueError("split requires exactly two pane children")
    return Split(*context.children, direction=context.attributes["direction"])


def _button_source(event: Button.Pressed) -> Button:
    return event.button


def _input_source(event: Input.Changed | Input.Submitted) -> Input:
    return event.input


def _checkbox_source(event: Checkbox.Changed) -> Checkbox:
    return event.checkbox


def default_component_registry() -> ComponentRegistry:
    registry = ComponentRegistry()
    registry.register(
        ComponentSpec(tag="vertical", factory=build_vertical, child_policy="widgets")
    )
    registry.register(
        ComponentSpec(tag="horizontal", factory=build_horizontal, child_policy="widgets")
    )
    registry.register(ComponentSpec(tag="label", factory=build_label, text_policy="text"))
    registry.register(
        ComponentSpec(
            tag="button",
            factory=build_button,
            text_policy="text",
            attributes={
                "variant": AttributeSpec(
                    enum("default", "primary", "success", "warning", "error"),
                    default="default",
                )
            },
            events={"pressed": EventSpec(Button.Pressed, _button_source)},
        )
    )
    registry.register(
        ComponentSpec(
            tag="input",
            factory=build_input,
            attributes={
                "value": AttributeSpec(default=""),
                "placeholder": AttributeSpec(default=""),
                "password": AttributeSpec(boolean, default=False),
                "max-length": AttributeSpec(integer(minimum=1)),
            },
            events={
                "changed": EventSpec(Input.Changed, _input_source),
                "submitted": EventSpec(Input.Submitted, _input_source),
            },
        )
    )
    registry.register(
        ComponentSpec(
            tag="checkbox",
            factory=build_checkbox,
            text_policy="text",
            attributes={"value": AttributeSpec(boolean, default=False)},
            events={"changed": EventSpec(Checkbox.Changed, _checkbox_source)},
        )
    )
    registry.register(ComponentSpec(
        tag="pane", factory=build_pane, child_policy="widgets",
        attributes={"min-size": AttributeSpec(integer(minimum=1), default=1), "size": AttributeSpec(integer(minimum=1))},
    ))
    registry.register(ComponentSpec(
        tag="split", factory=build_split, child_policy="widgets",
        attributes={"direction": AttributeSpec(enum("horizontal", "vertical"), default="horizontal")},
        events={"resized": EventSpec(Split.Resized, lambda event: event.split), "toggled": EventSpec(Split.Toggled, lambda event: event.split)},
    ))
    return registry
