"""Native choice, disclosure, progress, and separator adapters."""
from __future__ import annotations

from math import isfinite

from textual.content import Content
from textual.widgets import Collapsible, ProgressBar, RadioButton, RadioSet, Rule

from ..registry import AttributeSpec, BuildContext, ComponentRegistry, ComponentSpec, EventSpec, boolean, enum


def finite_number(*, positive: bool = False):
    def convert(raw: str) -> float:
        try:
            value = float(raw)
        except ValueError as error:
            raise ValueError(f"expected a finite number; got {raw!r}") from error
        if not isfinite(value) or (value <= 0 if positive else value < 0):
            condition = "positive finite" if positive else "nonnegative finite"
            raise ValueError(f"expected a {condition} number; got {raw!r}")
        return value

    return convert


def build_radio_button(context: BuildContext) -> RadioButton:
    return RadioButton(Content(context.text or ""), value=context.attributes["value"])


def build_radio_set(context: BuildContext) -> RadioSet:
    return RadioSet(*context.children)


def build_collapsible(context: BuildContext) -> Collapsible:
    return Collapsible(
        *context.children,
        title=context.attributes["title"],
        collapsed=context.attributes["collapsed"],
    )


def build_progress_bar(context: BuildContext) -> ProgressBar:
    bar = ProgressBar(
        total=context.attributes.get("total"),
        show_bar=context.attributes["show-bar"],
        show_percentage=context.attributes["show-percentage"],
        show_eta=context.attributes["show-eta"],
    )
    bar.update(progress=context.attributes["progress"])
    return bar


def build_rule(context: BuildContext) -> Rule:
    return Rule(
        orientation=context.attributes["orientation"],
        line_style=context.attributes["line-style"],
    )


def register_display_controls(registry: ComponentRegistry) -> None:
    registry.register(ComponentSpec(
        tag="radio-button", factory=build_radio_button, text_policy="text",
        attributes={"value": AttributeSpec(boolean, default=False)},
        events={"changed": EventSpec(RadioButton.Changed, lambda event: event.radio_button)},
    ))
    registry.register(ComponentSpec(
        tag="radio-set", factory=build_radio_set, child_policy="widgets",
        events={"changed": EventSpec(RadioSet.Changed, lambda event: event.radio_set)},
    ))
    registry.register(ComponentSpec(
        tag="collapsible", factory=build_collapsible, child_policy="widgets",
        attributes={
            "title": AttributeSpec(default="Toggle"),
            "collapsed": AttributeSpec(boolean, default=True),
        },
        events={
            "collapsed": EventSpec(Collapsible.Collapsed, lambda event: event.collapsible),
            "expanded": EventSpec(Collapsible.Expanded, lambda event: event.collapsible),
        },
    ))
    registry.register(ComponentSpec(
        tag="progress-bar", factory=build_progress_bar,
        attributes={
            "total": AttributeSpec(finite_number(positive=True)),
            "progress": AttributeSpec(finite_number(), default=0.0),
            "show-bar": AttributeSpec(boolean, default=True),
            "show-percentage": AttributeSpec(boolean, default=True),
            "show-eta": AttributeSpec(boolean, default=True),
        },
    ))
    registry.register(ComponentSpec(
        tag="rule", factory=build_rule,
        attributes={
            "orientation": AttributeSpec(enum("horizontal", "vertical"), default="horizontal"),
            "line-style": AttributeSpec(enum("ascii", "blank", "dashed", "double", "heavy", "hidden", "none", "solid", "thick"), default="solid"),
        },
    ))
