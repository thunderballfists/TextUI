"""Interpret ordered content metadata and retain named compound checks."""
from __future__ import annotations

from collections.abc import Iterable

from ..errors import DocumentValidationError
from ..nodes import ElementNode
from .data_widgets import build_column, build_row
from .display_controls import build_radio_button, build_radio_set


def is_builtin(node: ElementNode, factory: object) -> bool:
    return node.spec.factory is factory


def validate_control_structure(nodes: Iterable[ElementNode]) -> None:
    from .metadata import content_for

    def visit(node: ElementNode, parent: ElementNode | None) -> None:
        content = content_for(node.spec)
        if content is not None:
            content.validate(node, parent)
        for child in node.children:
            visit(child, node)

    for root in nodes:
        visit(root, None)
    accelerators = [node.attributes["accelerator"] for node in walk(nodes) if node.spec.tag == "tab-pane" and "accelerator" in node.attributes]
    if len(accelerators) != len(set(accelerators)):
        raise DocumentValidationError("document accelerators must be unique")

def select_values(node: ElementNode, parent: ElementNode | None) -> None:
    values = [child.attributes['value'] for child in node.children]
    if len(values) != len(set(values)):
        raise DocumentValidationError('select option values must be unique', location=node.location)
    if 'value' in node.attributes and node.attributes['value'] not in values:
        raise DocumentValidationError('select value must match an option', location=node.location, attribute='value')

def initial_tab(node: ElementNode, parent: ElementNode | None) -> None:
    initial = node.attributes.get('initial')
    if initial is not None and initial not in {child.common['id'] for child in node.children}:
        raise DocumentValidationError('initial tab must name a child pane', location=node.location, attribute='initial')

def radio_selection(node: ElementNode, parent: ElementNode | None) -> None:
    if sum((bool(child.attributes['value']) for child in node.children)) > 1:
        raise DocumentValidationError('radio-set accepts at most one selected button', location=node.location)

def progress_bounds(node: ElementNode, parent: ElementNode | None) -> None:
    total = node.attributes.get('total')
    if total is not None and node.attributes['progress'] > total:
        raise DocumentValidationError('progress cannot exceed total', location=node.location, attribute='progress')

def range_bounds(node: ElementNode, parent: ElementNode | None) -> None:
    minimum = node.attributes['min']
    maximum = node.attributes['max']
    step = node.attributes['step']
    value = node.attributes.get('value', minimum)
    if minimum >= maximum:
        raise DocumentValidationError('range min must be less than max', location=node.location, attribute='min')
    if (maximum - minimum) % step:
        raise DocumentValidationError('range step must divide the declared bounds', location=node.location, attribute='step')
    if not minimum <= value <= maximum:
        raise DocumentValidationError('range value must be within min and max', location=node.location, attribute='value')
    if (value - minimum) % step:
        raise DocumentValidationError('range value must align to step', location=node.location, attribute='value')

def radio_events(node: ElementNode, parent: ElementNode | None) -> None:
    if is_builtin(node, build_radio_button) and parent is not None and is_builtin(parent, build_radio_set) and node.events:
        raise DocumentValidationError('radio-button inside radio-set cannot declare events; use on-changed on radio-set', location=node.location)

def table_requires_columns(node: ElementNode, parent: ElementNode | None) -> None:
    columns = [child for child in node.children if is_builtin(child, build_column)]
    rows = [child for child in node.children if is_builtin(child, build_row)]
    if rows and (not columns):
        raise DocumentValidationError('data-table rows require columns', location=node.location)

def table_keys_and_widths(node: ElementNode, parent: ElementNode | None) -> None:
    columns = [child for child in node.children if is_builtin(child, build_column)]
    rows = [child for child in node.children if is_builtin(child, build_row)]
    for kind, children in (('column', columns), ('row', rows)):
        keys = [child.attributes['key'] for child in children]
        if len(keys) != len(set(keys)):
            raise DocumentValidationError(f'data-table {kind} keys must be unique', location=node.location)
    for row in rows:
        if len(row.children) != len(columns):
            raise DocumentValidationError('row cell count must match column count', location=row.location)

def tree_keys(node: ElementNode, parent: ElementNode | None) -> None:
    keys = [descendant.attributes['key'] for descendant in _tree_nodes(node)]
    if len(keys) != len(set(keys)):
        raise DocumentValidationError('tree-node keys must be unique within a tree', location=node.location)

def walk(nodes: Iterable[ElementNode]) -> Iterable[ElementNode]:
    for node in nodes:
        yield node
        yield from walk(node.children)


def _tree_nodes(node: ElementNode) -> Iterable[ElementNode]:
    for child in node.children:
        if child.spec.tag == "tree-node":
            yield child
            yield from _tree_nodes(child)
