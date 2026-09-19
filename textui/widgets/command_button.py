"""Markup button adapter backed by a linked-script command."""
from __future__ import annotations

from textual.content import Content
from textual.widgets import Button

from ..registry import AttributeSpec, BuildContext, ComponentRegistry, ComponentSpec, enum


def _command_name(value: str) -> str:
    if not value.isidentifier():
        raise ValueError(f"expected a Python identifier; got {value!r}")
    return value


def build_command_button(context: BuildContext) -> Button:
    """Build a native button so ordinary `Button` TCSS selectors still apply."""
    button = Button(Content(""), variant=context.attributes["variant"])
    button._textui_command_name = context.attributes["command"]
    return button


def register_command_button(registry: ComponentRegistry) -> None:
    registry.register(ComponentSpec(
        tag="command-button",
        factory=build_command_button,
        attributes={
            "command": AttributeSpec(_command_name, required=True),
            "variant": AttributeSpec(enum("default", "primary", "success", "warning", "error"), default="default"),
        },
    ))
