# Runtime Data-Table Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Work in an isolated worktree and do not begin implementation while saving this plan.

**Goal:** Complete issue #28 with markup-defined table columns and an atomic `set_rows()` API for runtime API records.

**Architecture:** Extend `SeededDataTable`, the existing native `DataTable` adapter. Markup continues to define columns and optional seed rows; controllers call `set_rows()` to replace only rows. The adapter validates a complete batch before altering native state, retains a read-only copy of each source record, and delegates composition, scrolling, selection, and rendering to Textual.

**Tech Stack:** Python 3.11+, Textual 8.2.8, Rich `Text`, pytest, pytest-asyncio, Textual Pilot.

**Spec:** [GitHub issue #28](https://github.com/thunderballfists/TextUI/issues/28) and the Contract Decisions section below.

## Global Constraints

- Python `>=3.11,<4`; Textual `>=8.2.8,<9`; lxml `>=6.1.3,<7`.
- Use the existing native `DataTable`; add no runtime dependency.
- Keep strict XML, literal text, and explicit linked-Python actions. Do not add expressions or embedded Python.
- Existing `<column key="name">Name</column>`, `<row>`, native `add_row()`, and selection events remain compatible.
- Normal pytest remains headless and does not create screenshots.
- Use four-space indentation and update `CHANGELOG.md`, `README.md`, `docs/controls.md`, and the data example for user-visible markup or controller APIs.

## Contract Decisions

```xml
<data-table id="usage" row-key="record_id" on-row-selected="show_usage">
  <column key="date" label="Date" />
  <column key="requests" label="Reqs" align="right" width="8" />
  <column key="cost_usd" label="Cost" align="right" />
</data-table>
```

```python
usage = window.document.get_by_id("usage")
usage.set_rows(records)
record = usage.get_record(context.event.row_key.value)
```

- `row-key` is optional markup so static and native-managed tables remain valid; `set_rows()` raises `DocumentStateError` unless it is declared.
- `label` defaults to literal column text. `align` accepts `left`, `center`, or `right` and defaults to `left`. `width` is an optional positive integer passed to native `add_column()`.
- `set_rows(rows: Iterable[Mapping[str, object]]) -> None` requires every record to contain the non-empty string `row-key` and every declared column key. Duplicate row keys and missing keys raise `ValueError` before the current table changes. Extra record fields are retained in `get_record()` but do not create columns.
- A `None` cell renders as an empty literal cell; missing differs from `None` and is rejected. Other cell values render with `str(value)` as literal `Text`.
- `get_record(row_key: str) -> Mapping[str, object]` returns a read-only copy of the runtime record. It raises `KeyError` for a key absent from the current runtime batch.
- Replacement clears rows while preserving columns. If the prior cursor's row key remains, restore that row and its current column; otherwise use native coordinate `(0, 0)`. An empty batch leaves columns visible and has no selected record.
- Header-click sorting and arbitrary empty-state slots are deferred. Native `DataTable.sort()` remains available, but this task does not add a sorting policy or markup event.

## Review Focus

1. A late invalid record must not partially replace visible API data; Task 2 proves full-batch validation before mutation.
2. Duplicate, empty, numeric, and `None` row keys must not collapse records or produce an ambiguous selection; Task 2 rejects them with deterministic errors.
3. Missing declared fields must fail while extra API fields remain retrievable; Task 2 verifies both cases.
4. Refreshes must preserve selection by stable row key even when order changes; Task 3 verifies the retained and disappeared-key paths.
5. A `row-key` omission must not break static tables or silently invent unstable runtime keys; Task 1 verifies static compatibility and Task 2 verifies the runtime error.

---

## File Map

- `textui/widgets/data_widgets.py`: typed column metadata and the `SeededDataTable` runtime-row adapter.
- `textui/widgets/structure.py`: data-table child validation; retain its current ordering and uniqueness checks.
- `tests/test_data_widgets.py`: loader, mounted runtime, validation, selection, and remount regression tests.
- `examples/data/app.ui` and `examples/data/controller.py`: runnable usage/cost-style API refresh.
- `README.md`, `docs/controls.md`, `docs/project-runtime.md`, `CHANGELOG.md`: public markup and runtime API reference.

## Task 1: Add Column and Table Runtime Metadata

**Files:**
- Modify: `textui/widgets/data_widgets.py:16-70`
- Modify: `tests/test_data_widgets.py:1-64`

**Interfaces:**
- Consumes: existing `ComponentSpec`, `AttributeSpec`, `integer`, `enum`, and `DataTable.add_column(label, width, key)`.
- Produces: `TableColumn(label: str, key: str, align: str, width: int | None)`, `SeededDataTable(..., row_key: str | None)`, and `build_data_table()` carrying `row-key` into the table.

- [ ] **Step 1: Write loader and composition regressions**

```python
def test_data_table_column_metadata_and_optional_runtime_key_lower():
    document = DocumentLoader().from_string('''<ui>
      <data-table id="usage" row-key="record_id">
        <column key="date" label="Date" />
        <column key="requests" label="Reqs" align="right" width="8" />
      </data-table>
    </ui>''')
    table = document.nodes[0]
    assert table.attributes["row-key"] == "record_id"
    assert table.children[0].attributes["label"] == "Date"
    assert table.children[1].attributes["align"] == "right"
    assert table.children[1].attributes["width"] == 8


@pytest.mark.asyncio
async def test_column_metadata_uses_literal_label_width_and_alignment():
    app = TextUI(DocumentLoader().from_string('''<ui><data-table id="usage">
      <column key="requests" label="Reqs" align="right" width="8" />
    </data-table></ui>'''))
    async with app.run_test():
        column = app.document.get_by_id("usage").columns["requests"]
        assert column.label.plain == "Reqs"
        assert column.width == 8
```

- [ ] **Step 2: Run the regressions before implementation**

Run: `.venv/bin/python -m pytest tests/test_data_widgets.py::test_data_table_column_metadata_and_optional_runtime_key_lower tests/test_data_widgets.py::test_column_metadata_uses_literal_label_width_and_alignment -q`

Expected: FAIL because `row-key`, `label`, `align`, and `width` are unknown attributes.

- [ ] **Step 3: Add only the typed markup metadata**

```python
class TableColumn(Widget):
    def __init__(self, label: str, key: str, *, align: str, width: int | None) -> None:
        super().__init__()
        self.label = label
        self.key = key
        self.align = align
        self.width = width


def build_column(context: BuildContext) -> TableColumn:
    return TableColumn(
        context.attributes.get("label", context.text or ""),
        context.attributes["key"],
        align=context.attributes["align"],
        width=context.attributes.get("width"),
    )
```

Register `label` as an optional string, `align` as `enum("left", "center", "right")` with default `"left"`, `width` as `integer(minimum=1)`, and `row-key` as `nonempty_key`. Use the existing text when `label` is omitted. Pass `column.width` to native `add_column()` and preserve literal labels with `Text(column.label)`.

- [ ] **Step 4: Add invalid-attribute cases and run the focused suite**

```python
@pytest.mark.parametrize("markup", [
    '<ui><data-table row-key=""><column key="x">X</column></data-table></ui>',
    '<ui><data-table><column key="x" align="decimal">X</column></data-table></ui>',
    '<ui><data-table><column key="x" width="0">X</column></data-table></ui>',
])
def test_data_table_runtime_metadata_rejects_invalid_values(markup):
    with pytest.raises(DocumentValidationError):
        DocumentLoader().from_string(markup)
```

Run: `.venv/bin/python -m pytest tests/test_data_widgets.py -q`

Expected: PASS, with seeded markup and empty native-managed tables unchanged.

- [ ] **Step 5: Commit the markup metadata**

```sh
git add textui/widgets/data_widgets.py tests/test_data_widgets.py
git commit -m "Add runtime table column metadata"
```

## Task 2: Implement Atomic Runtime Row Replacement

**Files:**
- Modify: `textui/widgets/data_widgets.py:46-70`
- Modify: `tests/test_data_widgets.py`

**Interfaces:**
- Consumes: `SeededDataTable.row_key_field: str | None`, ordered `TableColumn` values, and native `clear(columns=False)`, `add_row()`, `coordinate_to_cell_key()`, and `move_cursor()`.
- Produces: `SeededDataTable.set_rows(rows: Iterable[Mapping[str, object]]) -> None` and `SeededDataTable.get_record(row_key: str) -> Mapping[str, object]`.

- [ ] **Step 1: Write a mounted replacement test with literal rendering and record lookup**

```python
@pytest.mark.asyncio
async def test_set_rows_replaces_seed_data_and_exposes_source_record():
    markup = '''<ui><data-table id="usage" row-key="record_id">
      <column key="date" label="Date" />
      <column key="requests" label="Reqs" align="right" width="8" />
      <row key="seed"><cell>old</cell><cell>0</cell></row>
    </data-table></ui>'''
    app = TextUI(DocumentLoader().from_string(markup))
    async with app.run_test():
        table = app.document.get_by_id("usage")
        table.set_rows([
            {"record_id": "2026-09-19-a", "date": "2026-09-19", "requests": 12, "source": "api"},
            {"record_id": "2026-09-19-b", "date": "2026-09-20", "requests": None},
        ])
        assert list(key.value for key in table.rows) == ["2026-09-19-a", "2026-09-19-b"]
        assert table.get_cell("2026-09-19-a", "requests").plain == "12"
        assert table.get_cell("2026-09-19-b", "requests").plain == ""
        assert dict(table.get_record("2026-09-19-a")) == {
            "record_id": "2026-09-19-a", "date": "2026-09-19", "requests": 12, "source": "api",
        }
```

- [ ] **Step 2: Run it before implementation**

Run: `.venv/bin/python -m pytest tests/test_data_widgets.py::test_set_rows_replaces_seed_data_and_exposes_source_record -q`

Expected: FAIL with `AttributeError: 'SeededDataTable' object has no attribute 'set_rows'`.

- [ ] **Step 3: Validate the full batch, then replace rows**

```python
def set_rows(self, rows: Iterable[Mapping[str, object]]) -> None:
    if self.row_key_field is None:
        raise DocumentStateError("set_rows requires a data-table row-key")
    validated: list[tuple[str, Mapping[str, object], tuple[Text, ...]]] = []
    seen: set[str] = set()
    for index, record in enumerate(rows):
        if not isinstance(record, Mapping):
            raise ValueError(f"row {index} must be a mapping")
        missing = [column.key for column in self._seed_columns if column.key not in record]
        if missing:
            raise ValueError(f"row {index} is missing column {missing[0]!r}")
        key = record.get(self.row_key_field)
        if not isinstance(key, str) or not key:
            raise ValueError(f"row {index} has an invalid {self.row_key_field!r}")
        if key in seen:
            raise ValueError(f"duplicate row key {key!r}")
        seen.add(key)
        cells = tuple(Text("" if record[column.key] is None else str(record[column.key]), justify=column.align) for column in self._seed_columns)
        validated.append((key, MappingProxyType(dict(record)), cells))
    self._replace_validated_rows(validated)
```

Implement `_replace_validated_rows()` to capture the existing cursor row key only when the coordinate is valid, then call `clear(columns=False)`, replace the private record mapping, add the staged `Text` cells, and restore the old key and prior column when present. Do not mutate a row, record map, or cursor before the validation loop completes.

- [ ] **Step 4: Pin validation atomicity and empty-table behavior**

```python
@pytest.mark.asyncio
async def test_set_rows_rejects_invalid_batch_without_changing_current_rows():
    app = TextUI(DocumentLoader().from_string('''<ui><data-table id="usage" row-key="id">
      <column key="name">Name</column><row key="seed"><cell>Seed</cell></row>
    </data-table></ui>'''))
    async with app.run_test():
        table = app.document.get_by_id("usage")
        with pytest.raises(ValueError, match="missing column 'name'"):
            table.set_rows([{"id": "ok", "name": "Ready"}, {"id": "bad"}])
        assert table.get_cell("seed", "name").plain == "Seed"
        table.set_rows([])
        assert len(table.rows) == 0
        assert len(table.columns) == 1
        with pytest.raises(KeyError):
            table.get_record("seed")
```

Add separate literal cases for missing `row-key`, `None`, empty, numeric, duplicate keys, non-mapping rows, and a table with no `row-key`. Assert all failures retain the prior native row and record state.

Run: `.venv/bin/python -m pytest tests/test_data_widgets.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the replacement API**

```sh
git add textui/widgets/data_widgets.py tests/test_data_widgets.py
git commit -m "Add atomic runtime table rows"
```

## Task 3: Preserve Runtime Selection and Document API Data Use

**Files:**
- Modify: `tests/test_data_widgets.py`
- Modify: `examples/data/app.ui`
- Modify: `examples/data/controller.py`
- Modify: `README.md:78`
- Modify: `docs/controls.md:52-69`
- Modify: `docs/project-runtime.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: `set_rows()` and `get_record()` from Task 2, existing `DataTable.RowSelected` forwarding, and `window.document.get_by_id()`.
- Produces: selection-preserving refresh behavior and a runnable runtime-row example.

- [ ] **Step 1: Write selection-restoration regressions**

```python
@pytest.mark.asyncio
async def test_set_rows_restores_cursor_by_stable_key_or_uses_first_row():
    app = TextUI(DocumentLoader().from_string('''<ui><data-table id="usage" row-key="id">
      <column key="name">Name</column><column key="count">Count</column>
    </data-table></ui>'''))
    async with app.run_test() as pilot:
        table = app.document.get_by_id("usage")
        table.set_rows([{"id": "a", "name": "Alpha", "count": 1}, {"id": "b", "name": "Bravo", "count": 2}])
        table.move_cursor(row=1, column=1, animate=False)
        table.set_rows([{"id": "b", "name": "Bravo", "count": 3}, {"id": "a", "name": "Alpha", "count": 4}])
        assert table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value == "b"
        assert table.cursor_column == 1
        table.set_rows([{"id": "a", "name": "Alpha", "count": 5}])
        assert table.cursor_coordinate == Coordinate(0, 0)
```

- [ ] **Step 2: Run it before selection restoration exists**

Run: `.venv/bin/python -m pytest tests/test_data_widgets.py::test_set_rows_restores_cursor_by_stable_key_or_uses_first_row -q`

Expected: FAIL because native `clear()` resets the cursor to `(0, 0)` even when the selected key remains.

- [ ] **Step 3: Restore only a surviving key after native replacement**

```python
if previous_key in self.rows:
    column = min(previous_column, len(self.columns) - 1)
    self.move_cursor(row=self.get_row_index(previous_key), column=column, animate=False)
```

Keep native `(0, 0)` for a missing key or empty rows. Do not synthesize an event while restoring cursor state.

- [ ] **Step 4: Convert the data example to runtime API records**

```python
@action
def refresh_usage():
    window.document.get_by_id("usage").set_rows([
        {"record_id": "2026-09-19-alpha", "date": "2026-09-19", "requests": 42, "cost_usd": 1.25},
        {"record_id": "2026-09-19-bravo", "date": "2026-09-19", "requests": 17, "cost_usd": 0.48},
    ])


@action
def usage_selected(context):
    usage = window.document.get_by_id("usage")
    record = usage.get_record(context.event.row_key.value)
    window.document.get_by_id("feedback").update(f"{record['date']}: {record['requests']} requests")
```

Use a `<data-table id="usage" row-key="record_id">` with `label`, `align`, and `width` attributes. Keep the existing table/tree seed example if it demonstrates native one-off mutation; add the runtime refresh beside it rather than removing unrelated tree coverage.

- [ ] **Step 5: Document complete syntax and run regression coverage**

Document the row-key requirement, atomic validation rules, `None` rendering, extra-field retention, selection fallback, and `get_record()` in `docs/controls.md` and `docs/project-runtime.md`. Update the README component table and add `Added`/`Changed` entries in `CHANGELOG.md`.

Run: `.venv/bin/python -m pytest tests/test_data_widgets.py tests/test_examples.py tests/test_project_app.py -q`

Expected: PASS, including the runnable data example.

- [ ] **Step 6: Run full verification and commit**

```sh
.venv/bin/python -m pytest -q
uvx --python 3.12 --from poetry==2.4.3 poetry check --lock
uvx --python 3.12 --from poetry==2.4.3 poetry build
git add textui/widgets/data_widgets.py tests/test_data_widgets.py examples/data README.md docs/controls.md docs/project-runtime.md CHANGELOG.md
git commit -m "Document runtime data table rows"
```

## Completion Gate

- [ ] Existing seed tables and direct native `add_row()` usage work unchanged.
- [ ] Markup columns accept literal `label`, `align`, and positive `width`; invalid values fail during load.
- [ ] `set_rows()` validates all records before replacement, handles empty batches, and never creates columns from unknown fields.
- [ ] Row keys are stable non-empty strings, current record lookup is read-only, and selection is restored by retained key.
- [ ] The data example, public docs, changelog, focused tests, full suite, package check, and build all pass.

## Deferred

Arbitrary empty-state slots, header-click sorting, display format specifications, automatic numeric sorting policy, and a generic runtime repeater remain separate decisions. Native `DataTable.sort()` stays available for applications that explicitly choose its behavior.
