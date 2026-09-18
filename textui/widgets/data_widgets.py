"""Declarative seed data for native Textual tables and trees."""
from __future__ import annotations

from rich.text import Text
from textual.widget import Widget
from textual.widgets import DataTable, Tree

from ..registry import AttributeSpec, BuildContext, ComponentRegistry, ComponentSpec, EventSpec, boolean, enum


def nonempty_key(value: str) -> str:
    if not value:
        raise ValueError("key cannot be empty")
    return value


class TableColumn(Widget):
    def __init__(self, label: str, key: str) -> None:
        super().__init__()
        self.label = label
        self.key = key


class TableCell(Widget):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value


class TableRow(Widget):
    def __init__(self, key: str, cells: tuple[Widget, ...]) -> None:
        super().__init__()
        self.key = key
        self.cells = tuple(cell.value for cell in cells)


class TreeSeedNode(Widget):
    def __init__(self, key: str, label: str, expanded: bool, children: tuple[Widget, ...]) -> None:
        super().__init__()
        self.key = key
        self.label = label
        self.expanded = expanded
        self.seed_children = children


class SeededDataTable(DataTable):
    def __init__(self, columns: tuple[TableColumn, ...], rows: tuple[TableRow, ...], *, cursor_type: str) -> None:
        super().__init__(cursor_type=cursor_type)
        self._seed_columns = columns
        self._seed_rows = rows
        self._seeded = False

    def on_mount(self) -> None:
        if self._seeded:
            return
        for column in self._seed_columns:
            self.add_column(Text(column.label), key=column.key)
        for row in self._seed_rows:
            self.add_row(*(Text(cell) for cell in row.cells), key=row.key)
        self._seeded = True


def build_data_table(context: BuildContext) -> DataTable:
    columns = tuple(child for child in context.children if isinstance(child, TableColumn))
    rows = tuple(child for child in context.children if isinstance(child, TableRow))
    return SeededDataTable(columns, rows, cursor_type=context.attributes["cursor-type"])


def build_column(context: BuildContext) -> TableColumn:
    return TableColumn(context.text or "", context.attributes["key"])


def build_cell(context: BuildContext) -> TableCell:
    return TableCell(context.text or "")


def build_row(context: BuildContext) -> TableRow:
    return TableRow(context.attributes["key"], context.children)


def build_tree_node(context: BuildContext) -> TreeSeedNode:
    return TreeSeedNode(
        context.attributes["key"], context.attributes["label"],
        context.attributes["expanded"], context.children,
    )


def build_tree(context: BuildContext) -> Tree[str]:
    tree: Tree[str] = Tree(Text(context.attributes["label"]))
    tree.show_root = context.attributes["show-root"]

    def add(parent, seed: TreeSeedNode) -> None:
        if seed.seed_children or seed.expanded:
            node = parent.add(Text(seed.label), data=seed.key, expand=seed.expanded)
            for child in seed.seed_children:
                add(node, child)
        else:
            parent.add_leaf(Text(seed.label), data=seed.key)

    for child in context.children:
        add(tree.root, child)
    tree.root.expand()
    return tree


def register_data_widgets(registry: ComponentRegistry) -> None:
    registry.register(ComponentSpec(
        tag="column", factory=build_column,
        text_policy="text", attributes={"key": AttributeSpec(nonempty_key, required=True)},
    ))
    registry.register(ComponentSpec(
        tag="cell", factory=build_cell, text_policy="text",
    ))
    registry.register(ComponentSpec(
        tag="row", factory=build_row,
        child_policy="widgets", attributes={"key": AttributeSpec(nonempty_key, required=True)},
    ))
    registry.register(ComponentSpec(
        tag="data-table", factory=build_data_table, child_policy="widgets",
        attributes={"cursor-type": AttributeSpec(enum("cell", "row", "column", "none"), default="row")},
        events={
            "row-selected": EventSpec(DataTable.RowSelected, lambda event: event.data_table),
            "cell-selected": EventSpec(DataTable.CellSelected, lambda event: event.data_table),
        },
    ))
    registry.register(ComponentSpec(
        tag="tree-node", factory=build_tree_node,
        child_policy="widgets",
        attributes={
            "key": AttributeSpec(nonempty_key, required=True),
            "label": AttributeSpec(required=True),
            "expanded": AttributeSpec(boolean, default=False),
        },
    ))
    registry.register(ComponentSpec(
        tag="tree", factory=build_tree, child_policy="widgets",
        attributes={
            "label": AttributeSpec(required=True),
            "show-root": AttributeSpec(boolean, default=True),
        },
        events={"node-selected": EventSpec(Tree.NodeSelected, lambda event: event.control)},
    ))
