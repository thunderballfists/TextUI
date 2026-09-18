"""Validate compound controls after includes and IDs are lowered."""
from __future__ import annotations

from collections.abc import Iterable

from ..errors import DocumentValidationError
from ..nodes import ElementNode


def validate_control_structure(nodes: Iterable[ElementNode]) -> None:
    def visit(node: ElementNode, parent: str | None) -> None:
        tag = node.spec.tag
        if tag == "option":
            if parent != "select":
                raise DocumentValidationError("option must be a direct child of select", location=node.location)
            if node.common["id"] is not None or node.common["classes"] or node.common["style"] is not None or node.common["disabled"]:
                raise DocumentValidationError("option accepts no common widget attributes", location=node.location)
        if tag == "select":
            if not node.children or any(child.spec.tag != "option" for child in node.children):
                raise DocumentValidationError("select requires option children", location=node.location)
            values = [child.attributes["value"] for child in node.children]
            if len(values) != len(set(values)):
                raise DocumentValidationError("select option values must be unique", location=node.location)
            if "value" in node.attributes and node.attributes["value"] not in values:
                raise DocumentValidationError("select value must match an option", location=node.location, attribute="value")
        if tag == "tab-pane":
            if parent != "tabbed-content":
                raise DocumentValidationError("tab-pane must be a direct child of tabbed-content", location=node.location)
            if node.common["id"] is None:
                raise DocumentValidationError("tab-pane requires an id", location=node.location, attribute="id")
        if tag == "tabbed-content":
            if not node.children or any(child.spec.tag != "tab-pane" for child in node.children):
                raise DocumentValidationError("tabbed-content requires tab-pane children", location=node.location)
            initial = node.attributes.get("initial")
            if initial is not None and initial not in {child.common["id"] for child in node.children}:
                raise DocumentValidationError("initial tab must name a child pane", location=node.location, attribute="initial")
        for child in node.children:
            visit(child, tag)

    for root in nodes:
        visit(root, None)
