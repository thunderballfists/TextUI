"""Validate compound controls after includes and IDs are lowered."""
from __future__ import annotations

from collections.abc import Iterable

from ..errors import DocumentValidationError
from ..nodes import ElementNode
from .data_widgets import build_cell, build_column, build_data_table, build_row, build_tree, build_tree_node
from .display_controls import build_progress_bar, build_radio_button, build_radio_set
from .form_controls import build_option, build_select
from .tabbed import build_tab_pane, build_tabbed_content
from .bars import SLOT_FACTORIES, build_bar


def validate_control_structure(nodes: Iterable[ElementNode]) -> None:
    def is_builtin(node: ElementNode, factory: object) -> bool:
        return node.spec.factory is factory

    def visit(node: ElementNode, parent: ElementNode | None) -> None:
        if is_builtin(node, build_option):
            if parent is None or not is_builtin(parent, build_select):
                raise DocumentValidationError("option must be a direct child of select", location=node.location)
            if node.common["id"] is not None or node.common["classes"] or node.common["style"] is not None or node.common["disabled"]:
                raise DocumentValidationError("option accepts no common widget attributes", location=node.location)
        if is_builtin(node, build_select):
            if not node.children or any(not is_builtin(child, build_option) for child in node.children):
                raise DocumentValidationError("select requires option children", location=node.location)
            values = [child.attributes["value"] for child in node.children]
            if len(values) != len(set(values)):
                raise DocumentValidationError("select option values must be unique", location=node.location)
            if "value" in node.attributes and node.attributes["value"] not in values:
                raise DocumentValidationError("select value must match an option", location=node.location, attribute="value")
        if is_builtin(node, build_tab_pane):
            if parent is None or not is_builtin(parent, build_tabbed_content):
                raise DocumentValidationError("tab-pane must be a direct child of tabbed-content", location=node.location)
            if node.common["id"] is None:
                raise DocumentValidationError("tab-pane requires an id", location=node.location, attribute="id")
            if "accelerator" in node.attributes and "accelerator-scope" not in node.attributes:
                raise DocumentValidationError("tab-pane accelerator requires accelerator-scope=document", location=node.location, attribute="accelerator-scope")
            if "accelerator-scope" in node.attributes and "accelerator" not in node.attributes:
                raise DocumentValidationError("accelerator-scope requires an accelerator", location=node.location, attribute="accelerator-scope")
        if is_builtin(node, build_tabbed_content):
            if not node.children or any(not is_builtin(child, build_tab_pane) for child in node.children):
                raise DocumentValidationError("tabbed-content requires tab-pane children", location=node.location)
            initial = node.attributes.get("initial")
            if initial is not None and initial not in {child.common["id"] for child in node.children}:
                raise DocumentValidationError("initial tab must name a child pane", location=node.location, attribute="initial")
        if is_builtin(node, build_radio_button) and parent is not None and is_builtin(parent, build_radio_set) and node.events:
            raise DocumentValidationError("radio-button inside radio-set cannot declare events; use on-changed on radio-set", location=node.location)
        if is_builtin(node, build_radio_set):
            if not node.children or any(not is_builtin(child, build_radio_button) for child in node.children):
                raise DocumentValidationError("radio-set requires radio-button children", location=node.location)
            if sum(bool(child.attributes["value"]) for child in node.children) > 1:
                raise DocumentValidationError("radio-set accepts at most one selected button", location=node.location)
        if is_builtin(node, build_progress_bar):
            total = node.attributes.get("total")
            if total is not None and node.attributes["progress"] > total:
                raise DocumentValidationError("progress cannot exceed total", location=node.location, attribute="progress")
        is_slot = node.spec.tag in SLOT_FACTORIES and node.spec.factory is SLOT_FACTORIES[node.spec.tag]
        is_bar = node.spec.tag in {"header", "status-bar"} and node.spec.factory is build_bar
        if is_slot and (parent is None or parent.spec.factory is not build_bar):
            raise DocumentValidationError("slot must be a direct child of header or status-bar", location=node.location)
        if is_bar:
            slots = [child.spec.tag for child in node.children]
            if any(slot not in SLOT_FACTORIES for slot in slots):
                raise DocumentValidationError("header accepts only left, center, and right slots", location=node.location)
            if len(slots) != len(set(slots)):
                raise DocumentValidationError("header accepts each slot at most once", location=node.location)
        if is_builtin(node, build_column) and (parent is None or not is_builtin(parent, build_data_table)):
            raise DocumentValidationError("column has an invalid parent", location=node.location)
        if is_builtin(node, build_row) and (parent is None or not is_builtin(parent, build_data_table)):
            raise DocumentValidationError("row has an invalid parent", location=node.location)
        if is_builtin(node, build_cell) and (parent is None or not is_builtin(parent, build_row)):
            raise DocumentValidationError("cell has an invalid parent", location=node.location)
        if is_builtin(node, build_tree_node) and (parent is None or not (is_builtin(parent, build_tree) or is_builtin(parent, build_tree_node))):
            raise DocumentValidationError("tree-node has an invalid parent", location=node.location)
        if any(is_builtin(node, factory) for factory in (build_column, build_row, build_cell, build_tree_node)):
            if node.common["id"] is not None or node.common["classes"] or node.common["style"] is not None or node.common["disabled"] or node.events:
                raise DocumentValidationError("data-only children accept no common widget attributes or events", location=node.location)
        if is_builtin(node, build_row) and any(not is_builtin(child, build_cell) for child in node.children):
            raise DocumentValidationError("row accepts only cell children", location=node.location)
        if is_builtin(node, build_data_table):
            columns = [child for child in node.children if is_builtin(child, build_column)]
            rows = [child for child in node.children if is_builtin(child, build_row)]
            if len(columns) + len(rows) != len(node.children):
                raise DocumentValidationError("data-table accepts only column and row children", location=node.location)
            if rows and not columns:
                raise DocumentValidationError("data-table rows require columns", location=node.location)
            if any(is_builtin(child, build_column) for child in node.children[len(columns):]):
                raise DocumentValidationError("data-table columns must precede rows", location=node.location)
            for kind, children in (("column", columns), ("row", rows)):
                keys = [child.attributes["key"] for child in children]
                if len(keys) != len(set(keys)):
                    raise DocumentValidationError(f"data-table {kind} keys must be unique", location=node.location)
            for row in rows:
                if len(row.children) != len(columns):
                    raise DocumentValidationError("row cell count must match column count", location=row.location)
        if (is_builtin(node, build_tree) or is_builtin(node, build_tree_node)) and any(not is_builtin(child, build_tree_node) for child in node.children):
            raise DocumentValidationError("tree accepts only tree-node children", location=node.location)
        if is_builtin(node, build_tree):
            keys = [descendant.attributes["key"] for descendant in _tree_nodes(node)]
            if len(keys) != len(set(keys)):
                raise DocumentValidationError("tree-node keys must be unique within a tree", location=node.location)
        for child in node.children:
            visit(child, node)

    for root in nodes:
        visit(root, None)
    accelerators = [node.attributes["accelerator"] for node in walk(nodes) if node.spec.tag == "tab-pane" and "accelerator" in node.attributes]
    if len(accelerators) != len(set(accelerators)):
        raise DocumentValidationError("document accelerators must be unique")


def walk(nodes: Iterable[ElementNode]) -> Iterable[ElementNode]:
    for node in nodes:
        yield node
        yield from walk(node.children)


def _tree_nodes(node: ElementNode) -> Iterable[ElementNode]:
    for child in node.children:
        if child.spec.tag == "tree-node":
            yield child
            yield from _tree_nodes(child)
