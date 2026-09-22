import pytest
from textual.app import App
from textual.widgets import DataTable, Tree
from textual.coordinate import Coordinate

from textui import DocumentLoader, DocumentStateError, DocumentValidationError, TextUI


MARKUP = '''<ui>
  <data-table id="jobs" cursor-type="row" on-row-selected="open_job">
    <column key="name">Name</column>
    <column key="state">State</column>
    <row key="job-1"><cell>Backup</cell><cell>Running</cell></row>
  </data-table>
  <tree id="files" label="Files" on-node-selected="open_file">
    <tree-node key="src" label="src" expanded="true">
      <tree-node key="app" label="app.py"/>
    </tree-node>
  </tree>
</ui>'''


def test_data_markup_lowers_with_typed_attributes():
    document = DocumentLoader().from_string(MARKUP)
    table, tree = document.nodes
    assert table.attributes["cursor-type"] == "row"
    assert table.children[2].children[0].text == "Backup"
    assert tree.children[0].attributes["expanded"] is True


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


def test_data_table_display_options_lower_as_booleans():
    document = DocumentLoader().from_string('''<ui>
      <data-table id="usage" striped="true" column-borders="true" resizable="true">
        <column key="requests" align="right">Requests</column>
      </data-table>
    </ui>''')
    table = document.nodes[0]
    assert table.attributes["striped"] is True
    assert table.attributes["column-borders"] is True
    assert table.attributes["resizable"] is True


@pytest.mark.asyncio
async def test_column_metadata_uses_literal_label_and_width():
    app = TextUI(DocumentLoader().from_string('''<ui><data-table id="usage">
      <column key="requests" label="Reqs" align="right" width="8" />
    </data-table></ui>'''))
    async with app.run_test():
        column = app.document.get_by_id("usage").columns["requests"]
        assert column.label.plain == "Reqs"
        assert column.width == 8


@pytest.mark.asyncio
async def test_column_alignment_applies_to_titles_and_seeded_cells():
    app = TextUI(DocumentLoader().from_string('''<ui><data-table id="usage">
      <column key="requests" align="right" width="8">Requests</column>
      <row key="today"><cell>42</cell></row>
    </data-table></ui>'''))
    async with app.run_test():
        table = app.document.get_by_id("usage")
        assert table.columns["requests"].label.justify == "right"
        assert table.get_cell("today", "requests").justify == "right"


@pytest.mark.asyncio
async def test_column_borders_render_between_headers_and_cells():
    app = TextUI(DocumentLoader().from_string('''<ui><data-table id="usage" column-borders="true">
      <column key="name">Name</column><column key="state">State</column>
      <row key="today"><cell>Alpha</cell><cell>Ready</cell></row>
    </data-table></ui>'''))
    async with app.run_test():
        table = app.document.get_by_id("usage")
        assert "│" in table.render_line(0).text
        assert "│" in table.render_line(1).text


@pytest.mark.asyncio
async def test_resizable_table_supports_keyboard_and_drag_without_sorting():
    app = TextUI(DocumentLoader().from_string('''<ui><data-table id="usage" resizable="true">
      <column key="name" width="8">Name</column><column key="state" width="8">State</column>
      <row key="zulu"><cell>Zulu</cell><cell>Ready</cell></row>
      <row key="alpha"><cell>Alpha</cell><cell>Queued</cell></row>
    </data-table></ui>'''))
    async with app.run_test(size=(40, 8)) as pilot:
        table = app.document.get_by_id("usage")
        first = table.columns["name"]
        table.focus()
        await pilot.press("ctrl+right")
        await pilot.pause()
        assert first.width == 9

        edge = first.get_render_width(table) - 1
        await pilot.mouse_down(table, offset=(edge, 0))
        end = (table.region.x + edge + 4, table.region.y)
        await pilot.hover(offset=end)
        await pilot.mouse_up(offset=end)
        await pilot.pause()
        assert first.width == 13
        assert [key.value for key in table.rows] == ["zulu", "alpha"]


@pytest.mark.asyncio
async def test_resizing_a_narrow_fixed_width_column_never_enlarges_it():
    app = TextUI(DocumentLoader().from_string('''<ui><data-table id="usage" resizable="true">
      <column key="id" width="2">ID</column>
    </data-table></ui>'''))
    async with app.run_test():
        table = app.document.get_by_id("usage")
        table.resize_column(0, -1)
        assert table.columns["id"].width == 2


@pytest.mark.asyncio
async def test_frozen_column_resize_edge_does_not_move_with_horizontal_scroll():
    app = TextUI(DocumentLoader().from_string('''<ui><data-table id="usage" resizable="true">
      <column key="id" width="8">ID</column><column key="name" width="20">Name</column>
    </data-table></ui>'''))
    async with app.run_test():
        table = app.document.get_by_id("usage")
        table.fixed_columns = 1
        expected = table._row_label_column_width + table.ordered_columns[0].get_render_width(table) - 1
        table.scroll_x = 4
        assert table._header_right_edge(0) == expected


@pytest.mark.parametrize("markup", [
    '<ui><data-table row-key=""><column key="x">X</column></data-table></ui>',
    '<ui><data-table><column key="x" align="decimal">X</column></data-table></ui>',
    '<ui><data-table><column key="x" width="0">X</column></data-table></ui>',
])
def test_data_table_runtime_metadata_rejects_invalid_values(markup):
    with pytest.raises(DocumentValidationError):
        DocumentLoader().from_string(markup)


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
        assert [key.value for key in table.rows] == ["2026-09-19-a", "2026-09-19-b"]
        assert table.get_cell("2026-09-19-a", "requests").plain == "12"
        assert table.get_cell("2026-09-19-b", "requests").plain == ""
        assert dict(table.get_record("2026-09-19-a")) == {
            "record_id": "2026-09-19-a",
            "date": "2026-09-19",
            "requests": 12,
            "source": "api",
        }
        with pytest.raises(TypeError):
            table.get_record("2026-09-19-a")["source"] = "changed"


@pytest.mark.asyncio
async def test_set_rows_rejects_invalid_batch_without_changing_current_rows():
    app = TextUI(DocumentLoader().from_string('''<ui><data-table id="usage" row-key="id">
      <column key="name">Name</column><row key="seed"><cell>Seed</cell></row>
    </data-table></ui>'''))
    async with app.run_test():
        table = app.document.get_by_id("usage")
        table.set_rows([{"id": "current", "name": "Current", "source": "api"}])
        with pytest.raises(ValueError, match="missing column 'name'"):
            table.set_rows([{"id": "ready", "name": "Ready"}, {"id": "bad"}])
        assert [key.value for key in table.rows] == ["current"]
        assert table.get_cell("current", "name").plain == "Current"
        assert dict(table.get_record("current")) == {
            "id": "current",
            "name": "Current",
            "source": "api",
        }

        table.set_rows([])
        assert len(table.rows) == 0
        assert len(table.columns) == 1
        with pytest.raises(KeyError):
            table.get_record("current")


@pytest.mark.asyncio
@pytest.mark.parametrize(("rows", "error", "match"), [
    ([{"name": "Missing"}], ValueError, "invalid 'id'"),
    ([{"id": None, "name": "None"}], ValueError, "invalid 'id'"),
    ([{"id": "", "name": "Empty"}], ValueError, "invalid 'id'"),
    ([{"id": 1, "name": "Numeric"}], ValueError, "invalid 'id'"),
    ([{"id": "duplicate", "name": "One"}, {"id": "duplicate", "name": "Two"}], DocumentStateError, "duplicate row-key"),
    (["not a mapping"], ValueError, "must be a mapping"),
])
async def test_set_rows_rejects_invalid_runtime_keys_without_replacing_rows(rows, error, match):
    app = TextUI(DocumentLoader().from_string('''<ui><data-table id="usage" row-key="id">
      <column key="name">Name</column>
    </data-table></ui>'''))
    async with app.run_test():
        table = app.document.get_by_id("usage")
        table.set_rows([{"id": "current", "name": "Current"}])
        with pytest.raises(error, match=match):
            table.set_rows(rows)
        assert [key.value for key in table.rows] == ["current"]
        assert table.get_cell("current", "name").plain == "Current"


@pytest.mark.asyncio
async def test_set_rows_without_row_key_uses_positional_keys():
    app = TextUI(DocumentLoader().from_string('''<ui><data-table id="usage">
      <column key="name">Name</column><row key="seed"><cell>Seed</cell></row>
    </data-table></ui>'''))
    async with app.run_test():
        table = app.document.get_by_id("usage")
        table.set_rows([{"name": "New"}, {"name": "Next"}])
        assert [key.value for key in table.rows] == ["0", "1"]
        assert table.get_cell("0", "name").plain == "New"


@pytest.mark.asyncio
async def test_keyless_runtime_sort_keeps_records_bound_to_their_original_keys():
    app = TextUI(DocumentLoader().from_string('''<ui><data-table id="usage">
      <column key="name">Name</column><column key="count">Count</column>
    </data-table></ui>'''))
    async with app.run_test() as pilot:
        table = app.document.get_by_id("usage")
        table.set_rows([
            {"name": "Zulu", "count": 2},
            {"name": "Alpha", "count": 1},
        ])
        column = table.columns["name"]
        table.post_message(DataTable.HeaderSelected(table, column.key, 0, column.label))
        await pilot.pause()
        table.post_message(DataTable.HeaderSelected(table, column.key, 0, column.label))
        await pilot.pause()
        assert table.get_record("0")["name"] == "Zulu"
        assert table.get_record("1")["name"] == "Alpha"


@pytest.mark.asyncio
async def test_duplicate_runtime_row_key_names_the_table_and_markup_location():
    app = TextUI(DocumentLoader().from_string('''<ui><data-table id="usage" row-key="id">
      <column key="name">Name</column>
    </data-table></ui>''', source_name="app.ui"))
    async with app.run_test():
        table = app.document.get_by_id("usage")
        with pytest.raises(DocumentStateError, match=r"app\.ui.*usage.*duplicate row-key 'id' value 'same'"):
            table.set_rows([{"id": "same", "name": "One"}, {"id": "same", "name": "Two"}])


@pytest.mark.asyncio
async def test_set_rows_restores_cursor_by_stable_key_or_uses_first_row():
    app = TextUI(DocumentLoader().from_string('''<ui><data-table id="usage" row-key="id">
      <column key="name">Name</column><column key="count">Count</column>
    </data-table></ui>'''))
    async with app.run_test():
        table = app.document.get_by_id("usage")
        table.set_rows([
            {"id": "a", "name": "Alpha", "count": 1},
            {"id": "b", "name": "Bravo", "count": 2},
        ])
        table.move_cursor(row=1, column=1, animate=False)
        table.set_rows([
            {"id": "b", "name": "Bravo", "count": 3},
            {"id": "a", "name": "Alpha", "count": 4},
        ])
        assert table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value == "b"
        assert table.cursor_column == 1

        table.set_rows([{"id": "a", "name": "Alpha", "count": 5}])
        assert table.cursor_coordinate == Coordinate(0, 0)


@pytest.mark.asyncio
async def test_runtime_table_header_sorts_source_values_and_toggles_direction():
    app = TextUI(DocumentLoader().from_string('''<ui><data-table id="usage" row-key="id">
      <column key="name">Name</column><column key="requests">Requests</column>
    </data-table></ui>'''))
    async with app.run_test() as pilot:
        table = app.document.get_by_id("usage")
        table.set_rows([
            {"id": "high", "name": "High", "requests": 42},
            {"id": "low", "name": "Low", "requests": 7},
            {"id": "middle", "name": "Middle", "requests": 12},
        ])
        column = table.columns["requests"]
        table.post_message(DataTable.HeaderSelected(table, column.key, 1, column.label))
        await pilot.pause()
        assert [key.value for key in table.rows] == ["low", "middle", "high"]
        assert table.columns["requests"].label.plain == "Requests ↑"
        assert not any("reverse" in str(span.style) for span in table.columns["requests"].label.spans)
        assert table._should_highlight(table.cursor_coordinate, Coordinate(-1, 1), "row")
        assert not table._should_highlight(table.cursor_coordinate, Coordinate(-1, 0), "row")
        assert table.get_component_styles("datatable--header-hover").rich_style.underline

        table.post_message(DataTable.HeaderSelected(table, column.key, 1, column.label))
        await pilot.pause()
        assert [key.value for key in table.rows] == ["high", "middle", "low"]
        assert table.columns["requests"].label.plain == "Requests ↓"

        name_column = table.columns["name"]
        table.post_message(DataTable.HeaderSelected(table, name_column.key, 0, name_column.label))
        await pilot.pause()
        assert [key.value for key in table.rows] == ["high", "low", "middle"]
        assert table.columns["name"].label.plain == "Name ↑"
        assert table.columns["requests"].label.plain == "Requests"


@pytest.mark.asyncio
async def test_set_rows_keeps_active_runtime_sort_on_refresh():
    app = TextUI(DocumentLoader().from_string('''<ui><data-table id="usage" row-key="id">
      <column key="name">Name</column><column key="requests">Requests</column>
    </data-table></ui>'''))
    async with app.run_test() as pilot:
        table = app.document.get_by_id("usage")
        table.set_rows([
            {"id": "high", "name": "High", "requests": 42},
            {"id": "low", "name": "Low", "requests": 7},
        ])
        column = table.columns["requests"]
        table.post_message(DataTable.HeaderSelected(table, column.key, 1, column.label))
        await pilot.pause()

        table.set_rows([
            {"id": "middle", "name": "Middle", "requests": 12},
            {"id": "high", "name": "High", "requests": 42},
            {"id": "low", "name": "Low", "requests": 7},
        ])
        assert [key.value for key in table.rows] == ["low", "middle", "high"]
        assert table.columns["requests"].label.plain == "Requests ↑"


@pytest.mark.asyncio
async def test_seeded_table_header_sorts_literal_cells():
    app = TextUI(DocumentLoader().from_string('''<ui><data-table id="jobs">
      <column key="name">Name</column>
      <row key="zulu"><cell>Zulu</cell></row>
      <row key="alpha"><cell>Alpha</cell></row>
    </data-table></ui>'''))
    async with app.run_test() as pilot:
        table = app.document.get_by_id("jobs")
        column = table.columns["name"]
        table.post_message(DataTable.HeaderSelected(table, column.key, 0, column.label))
        await pilot.pause()
        assert [row.key.value for row in table.ordered_rows] == ["alpha", "zulu"]


def test_data_widgets_can_be_composed_before_app_runs():
    bound = DocumentLoader().from_string(MARKUP).bind(App(), actions={
        "open_job": lambda context: None,
        "open_file": lambda context: None,
    })
    table, tree = list(bound.compose())
    assert isinstance(table, DataTable)
    assert isinstance(tree, Tree)


@pytest.mark.parametrize("markup", [
    '<ui><column key="x">X</column></ui>',
    '<ui><row key="r"><cell>X</cell></row></ui>',
    '<ui><cell>X</cell></ui>',
    '<ui><tree-node key="x" label="X"/></ui>',
    '<ui><data-table><row key="r"><cell>X</cell></row></data-table></ui>',
    '<ui><data-table><column key="x">X</column><column key="x">Again</column></data-table></ui>',
    '<ui><data-table><column key="x">X</column><row key="r"><cell>A</cell></row><row key="r"><cell>B</cell></row></data-table></ui>',
    '<ui><data-table><column key="x">X</column><row key="r"><cell>A</cell><cell>B</cell></row></data-table></ui>',
    '<ui><data-table><column key="x">X</column><row key="r"><cell>A</cell></row><column key="y">Y</column></data-table></ui>',
    '<ui><data-table><column key="x" id="bad">X</column></data-table></ui>',
    '<ui><data-table><column key="x" disabled="false">X</column></data-table></ui>',
    '<ui><data-table><column key="x" class="">X</column></data-table></ui>',
    '<ui><tree label="Files"><tree-node key="a" label="A"><tree-node key="a" label="Again"/></tree-node></tree></ui>',
    '<ui><tree label="Files"><tree-node key="a" label="A" id="bad"/></tree></ui>',
    '<ui><tree label="Files"><tree-node key="a" label="A" style=""/></tree></ui>',
    '<ui><tree label="Files"><label>Wrong</label></tree></ui>',
    '<ui><tree label="Files"><tree-node key="src" label="src"><label>Wrong</label></tree-node></tree></ui>',
    '<ui><data-table><column key="">Name</column></data-table></ui>',
    '<ui><tree label="Files"><tree-node key="" label="Empty"/></tree></ui>',
])
def test_data_markup_rejects_invalid_structure(markup):
    with pytest.raises(DocumentValidationError):
        DocumentLoader().from_string(markup)


@pytest.mark.asyncio
async def test_native_data_widgets_seed_selection_and_mutation():
    events = []
    app = TextUI(DocumentLoader().from_string(MARKUP), actions={
        "open_job": lambda context: events.append(("row", context.event.row_key.value)),
        "open_file": lambda context: events.append(("node", context.event.node.data)),
    })
    async with app.run_test(size=(80, 24)) as pilot:
        table = app.document.get_by_id("jobs")
        tree = app.document.get_by_id("files")
        assert isinstance(table, DataTable)
        assert table.get_cell("job-1", "name").plain == "Backup"
        assert isinstance(tree, Tree)
        assert tree.root.children[0].children[0].data == "app"

        table.focus()
        await pilot.press("enter")
        await pilot.pause()
        assert ("row", "job-1") in events

        tree.select_node(tree.root.children[0].children[0])
        await pilot.pause()
        assert ("node", "app") in events

        table.add_row("Deploy", "Queued", key="job-2")
        tree.root.add_leaf("README.md", data="readme")
        assert table.get_cell("job-2", "name") == "Deploy"
        assert tree.root.children[-1].data == "readme"


@pytest.mark.asyncio
async def test_cell_selection_uses_exact_table_and_native_event():
    seen = []
    markup = '''<ui>
      <data-table id="first" cursor-type="cell" on-cell-selected="selected">
        <column key="name">Name</column><row key="one"><cell>One</cell></row>
      </data-table>
      <data-table id="second" cursor-type="cell">
        <column key="name">Name</column><row key="two"><cell>Two</cell></row>
      </data-table>
    </ui>'''
    app = TextUI(DocumentLoader().from_string(markup), actions={
        "selected": lambda context: seen.append((context.widget.id, context.event.value.plain)),
    })
    async with app.run_test() as pilot:
        first = app.document.get_by_id("first")
        second = app.document.get_by_id("second")
        second.focus()
        await pilot.press("enter")
        first.focus()
        await pilot.press("enter")
        await pilot.pause()
        assert seen == [("first", "One")]


@pytest.mark.asyncio
async def test_empty_data_widgets_allow_runtime_population():
    app = TextUI(DocumentLoader().from_string('<ui><data-table id="table"/><tree id="tree" label="Root"/></ui>'))
    async with app.run_test():
        table = app.document.get_by_id("table")
        table.add_column("Name", key="name")
        table.add_row("New", key="new")
        tree = app.document.get_by_id("tree")
        tree.root.add_leaf("New", data="new")
        assert table.get_cell_at(Coordinate(0, 0)) == "New"
        assert tree.root.children[0].data == "new"


@pytest.mark.asyncio
async def test_seeded_table_can_be_removed_and_remounted():
    markup = '''<ui><data-table id="jobs">
      <column key="name">Name</column><row key="one"><cell>One</cell></row>
    </data-table></ui>'''
    app = TextUI(DocumentLoader().from_string(markup))
    async with app.run_test():
        table = app.document.get_by_id("jobs")
        await table.remove()
        await app.mount(table)
        assert table.get_cell("one", "name").plain == "One"
        assert len(table.columns) == 1
        assert len(table.rows) == 1


@pytest.mark.asyncio
async def test_seed_text_is_literal_even_when_it_looks_like_rich_markup():
    markup = '''<ui>
      <data-table id="jobs"><column key="name">[red]Name[/red]</column>
        <row key="one"><cell>[blue]One[/blue]</cell></row></data-table>
      <tree id="files" label="[red]Files[/red]">
        <tree-node key="app" label="[blue]app.py[/blue]"/>
      </tree>
    </ui>'''
    app = TextUI(DocumentLoader().from_string(markup))
    async with app.run_test():
        table = app.document.get_by_id("jobs")
        tree = app.document.get_by_id("files")
        assert table.columns["name"].label.plain == "[red]Name[/red]"
        assert table.get_cell("one", "name").plain == "[blue]One[/blue]"
        assert tree.root.label.plain == "[red]Files[/red]"
        assert tree.root.children[0].label.plain == "[blue]app.py[/blue]"
