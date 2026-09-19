"""Markup button adapter backed by a linked-script command."""
from __future__ import annotations

from textual.widgets import Button

from ..registry import AttributeSpec, BuildContext, ComponentRegistry, ComponentSpec, enum


def _command_name(value: str) -> str:
    if not value.isidentifier():
        raise ValueError(f"expected a Python identifier; got {value!r}")
    return value


class CommandButton(Button):
    """A button whose label and availability come from command metadata."""

    def __init__(self, command_name: str, *, variant: str) -> None:
        super().__init__("", variant=variant)
        self.command_name = command_name


def build_command_button(context: BuildContext) -> CommandButton:
    return CommandButton(context.attributes["command"], variant=context.attributes["variant"])


def register_command_button(registry: ComponentRegistry) -> None:
    registry.register(ComponentSpec(
        tag="command-button",
        factory=build_command_button,
        attributes={
            "command": AttributeSpec(_command_name, required=True),
            "variant": AttributeSpec(enum("default", "primary", "success", "warning", "error"), default="default"),
        },
    ))
