"""Declarative seed data for native Textual tables and trees."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from numbers import Real
from types import MappingProxyType

from rich.text import Text
from textual.coordinate import Coordinate
from textual.widget import Widget
from textual.widgets import DataTable, Tree

from ..errors import DocumentStateError
from ..registry import AttributeSpec, BuildContext, ComponentRegistry, ComponentSpec, EventSpec, boolean, enum, integer


def nonempty_key(value: str) -> str:
    if not value:
        raise ValueError("key cannot be empty")
    return value


class TableColumn(Widget):
    def __init__(self, label: str, key: str, *, align: str, width: int | None) -> None:
        super().__init__()
        self.label = label
        self.key = key
        self.align = align
        self.width = width


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
    DEFAULT_CSS = """
    SeededDataTable:focus > .datatable--header {
        background: $panel;
    }
    SeededDataTable > .datatable--header-hover {
        background: $accent 50%;
        color: $foreground;
        text-style: bold underline;
    }
    SeededDataTable > .datatable--header-cursor {
        background: $primary;
        color: $foreground;
        text-style: bold;
    }
    """

    def __init__(
        self,
        columns: tuple[TableColumn, ...],
        rows: tuple[TableRow, ...],
        *,
        cursor_type: str,
        row_key: str | None,
    ) -> None:
        super().__init__(cursor_type=cursor_type)
        self._seed_columns = columns
        self._seed_rows = rows
        self.row_key_field = row_key
        self._runtime_records: dict[str, Mapping[str, object]] = {}
        self._sort_column: str | None = None
        self._sort_reverse = False
        self._header_labels: dict[str, Text] = {}
        self._seeded = False

    def on_mount(self) -> None:
        if self._seeded:
            return
        for column in self._seed_columns:
            self.add_column(Text(column.label), width=column.width, key=column.key)
        for row in self._seed_rows:
            self.add_row(*(Text(cell) for cell in row.cells), key=row.key)
        self._seeded = True

    def set_rows(self, rows: Iterable[Mapping[str, object]]) -> None:
        if self.row_key_field is None:
            raise DocumentStateError("set_rows requires a data-table row-key")

        validated: list[tuple[str, Mapping[str, object], tuple[Text, ...]]] = []
        keys: set[str] = set()
        for index, record in enumerate(rows):
            if not isinstance(record, Mapping):
                raise ValueError(f"row {index} must be a mapping")
            missing = [column.key for column in self._seed_columns if column.key not in record]
            if missing:
                raise ValueError(f"row {index} is missing column {missing[0]!r}")
            key = record.get(self.row_key_field)
            if not isinstance(key, str) or not key:
                raise ValueError(f"row {index} has an invalid {self.row_key_field!r}")
            if key in keys:
                raise ValueError(f"duplicate row key {key!r}")
            keys.add(key)
            cells = tuple(
                Text(
                    "" if record[column.key] is None else str(record[column.key]),
                    justify=column.align,
                )
                for column in self._seed_columns
            )
            validated.append((key, MappingProxyType(dict(record)), cells))

        if self._sort_column is not None:
            validated.sort(
                key=lambda row: self._sort_value(row[1][self._sort_column]),
                reverse=self._sort_reverse,
            )
        previous_key: str | None = None
        previous_column: int | None = None
        if self.is_valid_coordinate(self.cursor_coordinate):
            previous_key = self.coordinate_to_cell_key(self.cursor_coordinate).row_key.value
            previous_column = self.cursor_column
        self.clear(columns=False)
        self._runtime_records = {key: record for key, record, _ in validated}
        for key, _, cells in validated:
            self.add_row(*cells, key=key)
        if previous_key in self.rows and previous_column is not None and self.columns:
            self.move_cursor(
                row=self.get_row_index(previous_key),
                column=min(previous_column, len(self.columns) - 1),
                animate=False,
            )

    def get_record(self, row_key: str) -> Mapping[str, object]:
        return self._runtime_records[row_key]

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        column_key = event.column_key.value
        if column_key not in {column.key for column in self._seed_columns}:
            return
        reverse = column_key == self._sort_column and not self._sort_reverse
        if self._runtime_records:
            self._sort_column = column_key
            self._sort_reverse = reverse
            self.set_rows(self._runtime_records.values())
        else:
            self.sort(
                event.column_key,
                key=lambda value: self._sort_value(value.plain if isinstance(value, Text) else value),
                reverse=reverse,
            )
            self._sort_column = column_key
            self._sort_reverse = reverse
        self._set_sort_indicator(column_key, reverse)
        event.stop()

    @staticmethod
    def _sort_value(value: object) -> tuple[int, float | str]:
        if isinstance(value, bool):
            return (0, float(value))
        if isinstance(value, Real):
            return (1, float(value))
        return (2, str(value).casefold())

    def _set_sort_indicator(self, column_key: str, reverse: bool) -> None:
        for key, column in self.columns.items():
            key_value = key.value
            label = self._header_labels.setdefault(key_value, column.label.copy())
            updated_label = label.copy()
            if key_value == column_key:
                updated_label.append(" ↓" if reverse else " ↑")
            column.label = updated_label
        self._require_update_dimensions = True
        self._update_count += 1
        self.check_idle()
        self.refresh()

    def _should_highlight(
        self,
        cursor: Coordinate,
        target_cell: Coordinate,
        type_of_cursor: str,
    ) -> bool:
        if (
            type_of_cursor == "row"
            and cursor == self.cursor_coordinate
            and target_cell.row == -1
            and self._sort_column is not None
        ):
            return target_cell.column == self.get_column_index(self._sort_column)
        return super()._should_highlight(cursor, target_cell, type_of_cursor)


def build_data_table(context: BuildContext) -> SeededDataTable:
    columns = tuple(child for child in context.children if isinstance(child, TableColumn))
    rows = tuple(child for child in context.children if isinstance(child, TableRow))
    return SeededDataTable(
        columns,
        rows,
        cursor_type=context.attributes["cursor-type"],
        row_key=context.attributes.get("row-key"),
    )


def build_column(context: BuildContext) -> TableColumn:
    return TableColumn(
        context.attributes.get("label", context.text or ""),
        context.attributes["key"],
        align=context.attributes["align"],
        width=context.attributes.get("width"),
    )


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
        text_policy="text",
        attributes={
            "key": AttributeSpec(nonempty_key, required=True),
            "label": AttributeSpec(),
            "align": AttributeSpec(enum("left", "center", "right"), default="left"),
            "width": AttributeSpec(integer(minimum=1)),
        },
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
        attributes={
            "cursor-type": AttributeSpec(enum("cell", "row", "column", "none"), default="row"),
            "row-key": AttributeSpec(nonempty_key),
        },
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
