"""Validate compound controls after includes and IDs are lowered."""
from __future__ import annotations

from collections.abc import Iterable

from ..errors import DocumentValidationError
from ..nodes import ElementNode
from .data_widgets import build_cell, build_column, build_data_table, build_row, build_tree, build_tree_node


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
        if tag == "radio-set":
            if not node.children or any(child.spec.tag != "radio-button" for child in node.children):
                raise DocumentValidationError("radio-set requires radio-button children", location=node.location)
            if sum(bool(child.attributes["value"]) for child in node.children) > 1:
                raise DocumentValidationError("radio-set accepts at most one selected button", location=node.location)
        if tag == "progress-bar":
            total = node.attributes.get("total")
            if total is not None and node.attributes["progress"] > total:
                raise DocumentValidationError("progress cannot exceed total", location=node.location, attribute="progress")
        data_factories = {"column": build_column, "row": build_row, "cell": build_cell, "tree-node": build_tree_node}
        is_data_child = tag in data_factories and node.spec.factory is data_factories[tag]
        is_data_table = tag == "data-table" and node.spec.factory is build_data_table
        is_tree = tag == "tree" and node.spec.factory is build_tree
        if is_data_child:
            expected = {"column": "data-table", "row": "data-table", "cell": "row", "tree-node": None}[tag]
            valid = parent in {"tree", "tree-node"} if tag == "tree-node" else parent == expected
            if not valid:
                raise DocumentValidationError(f"{tag} has an invalid parent", location=node.location)
            if node.common["id"] is not None or node.common["classes"] or node.common["style"] is not None or node.common["disabled"] or node.events:
                raise DocumentValidationError(f"{tag} accepts no common widget attributes or events", location=node.location)
        if tag == "row" and node.spec.factory is build_row and any(child.spec.tag != "cell" or child.spec.factory is not build_cell for child in node.children):
            raise DocumentValidationError("row accepts only cell children", location=node.location)
        if is_data_table:
            columns = [child for child in node.children if child.spec.tag == "column"]
            rows = [child for child in node.children if child.spec.tag == "row"]
            if len(columns) + len(rows) != len(node.children):
                raise DocumentValidationError("data-table accepts only column and row children", location=node.location)
            if rows and not columns:
                raise DocumentValidationError("data-table rows require columns", location=node.location)
            if any(child.spec.tag == "column" for child in node.children[len(columns):]):
                raise DocumentValidationError("data-table columns must precede rows", location=node.location)
            for kind, children in (("column", columns), ("row", rows)):
                keys = [child.attributes["key"] for child in children]
                if len(keys) != len(set(keys)):
                    raise DocumentValidationError(f"data-table {kind} keys must be unique", location=node.location)
            for row in rows:
                if len(row.children) != len(columns):
                    raise DocumentValidationError("row cell count must match column count", location=row.location)
        if (is_tree or (tag == "tree-node" and node.spec.factory is build_tree_node)) and any(child.spec.tag != "tree-node" or child.spec.factory is not build_tree_node for child in node.children):
            raise DocumentValidationError(f"{tag} accepts only tree-node children", location=node.location)
        if is_tree:
            keys = [descendant.attributes["key"] for descendant in _tree_nodes(node)]
            if len(keys) != len(set(keys)):
                raise DocumentValidationError("tree-node keys must be unique within a tree", location=node.location)
        for child in node.children:
            visit(child, tag)

    for root in nodes:
        visit(root, None)


def _tree_nodes(node: ElementNode) -> Iterable[ElementNode]:
    for child in node.children:
        if child.spec.tag == "tree-node":
            yield child
            yield from _tree_nodes(child)
