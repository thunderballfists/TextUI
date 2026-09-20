# Form controls and tabs

TextUI maps these tags to native Textual widgets. Their IDs work with `window.document.get_by_id(...)`, and an `on-*` attribute names an exposed action. Markup remains structural; controller code belongs in a linked `<script src="..."/>` file or an explicit host action mapping.

```xml
<ui>
  <select id="state" value="new" allow-blank="false" on-changed="state_changed">
    <option value="new">New</option>
    <option value="done">Done</option>
  </select>
  <switch id="enabled" value="true" on-changed="enabled_changed" />
  <text-area id="notes" soft-wrap="true" on-changed="notes_changed">First line
Second line</text-area>
</ui>
```

`<select>` requires one or more direct `<option>` children with unique string values. An explicit select `value` must match an option. With `allow-blank="false"` and no value, the first option is selected. Option labels are literal text, and an option is not a mounted document widget. `Select.Changed` exposes the selected value as `context.event.value`. Switch values use `true` or `false` and produce a `Switch.Changed` event with the same property.

`<text-area>` preserves its body text, including newlines and spaces. Unlike labels and buttons, it does not collapse whitespace. It rejects nested elements. Its `changed` event exposes the native TextArea as `context.event.text_area`; read current contents from `.text`. Attributes map to native Textual behavior: `soft-wrap`, `read-only`, `show-line-numbers`, `tab-behavior="focus|indent"`, `placeholder`, and optional `language`.

Static tab views use native `TabbedContent`:

```xml
<tabbed-content id="tabs" initial="home" on-tab-activated="tab_changed">
  <tab-pane id="home" title="Home"><label>Welcome</label></tab-pane>
  <tab-pane id="settings" title="Settings"><label>Preferences</label></tab-pane>
</tabbed-content>
```

Each pane needs an ID and title. `initial` must name one of those panes; without it, Textual selects the first. The `tab-activated` event provides `context.event.pane`. Tabs respond to native mouse and keyboard input. The [controls example](../examples/controls/app.ui) shows all four controls in a runnable project.

## Choices, disclosure, and indicators

```xml
<radio-set id="priority" on-changed="priority_changed">
  <radio-button id="low">Low</radio-button>
  <radio-button id="high" value="true">High</radio-button>
</radio-set>
<collapsible title="Details" collapsed="true" on-expanded="show_details">
  <label>Additional information</label>
</collapsible>
<progress-bar id="work" total="100" progress="25" show-eta="false" />
<range id="volume" min="0" max="100" step="5" value="40" show-value="true" on-changed="volume_changed" />
<rule orientation="horizontal" line-style="dashed" />
```

A radio set needs direct radio-button children and allows at most one initially selected button. Put `on-changed` on the set: its event provides `context.event.pressed` and `context.event.index`. A standalone radio button supports `on-changed`, but a button inside a set cannot declare events because Textual consumes its change message. Collapsible content uses native pointer and Enter-key toggling. Use `on-collapsed` and `on-expanded` for its two exact native message types.

Progress values are finite numbers. `total` must be positive when supplied, `progress` cannot be negative or exceed a declared total, and omitted `total` creates an indeterminate bar. Controller code can call `window.document.get_by_id("work").update(advance=5)`.

`<range>` is an integer slider. It defaults to `min="0"`, `max="100"`, `step="1"`, and a value equal to `min`. Its bounds must satisfy `min &lt; max`, and the step must divide the span so Home and End always reach exact bounds. Values must be within those bounds and aligned to the step. Arrow keys adjust by one step; Home and End set the bounds; mouse clicks and drags choose a value. Set `show-value="true"` to render the number. Controller code can read or assign `window.document.get_by_id("volume").value`; each change emits `context.event.value`. Style `RangeControl` or its `range--track`, `range--filled`, `range--thumb`, and `range--value` component classes in TCSS. A rule can be horizontal or vertical and accepts Textual line styles such as `solid`, `dashed`, `heavy`, and `double`. The [Indicators tab](../examples/controls/app.ui) demonstrates these widgets together.

## Tables and trees

Seed native `DataTable` and `Tree` widgets with nested markup. Keys identify table rows and columns and become each tree node's `data` value:

```xml
<data-table id="jobs" cursor-type="row" on-row-selected="open_job">
  <column key="name">Job</column>
  <column key="state">State</column>
  <row key="backup"><cell>Backup</cell><cell>Running</cell></row>
</data-table>
<tree id="files" label="Files" on-node-selected="open_file">
  <tree-node key="src" label="src" expanded="true">
    <tree-node key="app" label="app.py"/>
  </tree-node>
</tree>
```

Columns must precede rows. Each row needs one cell per column; column and row keys must be unique within their table, and tree-node keys must be unique within their tree. `<column>`, `<row>`, `<cell>`, and `<tree-node>` are seed data, not mounted widgets, so they cannot have document IDs or common widget attributes. Seed labels and cells are literal text, even when they contain Rich-style brackets; native table cell values are `Text` objects, so read their `.plain` property for a string. Empty tables and trees may be populated entirely in Python. Table `cursor-type` accepts `row` (default), `cell`, `column`, or `none`; use `on-cell-selected` for cell cursors. Row events expose `context.event.row_key.value`, cell events expose `context.event.value` and `cell_key`, and tree events expose `context.event.node.data`.

After mounting, use native APIs: `window.document.get_by_id("jobs").add_row("Deploy", "Queued", key="deploy")` or `window.document.get_by_id("files").root.add_leaf("README.md", data="readme")`.

For API records that replace a complete table, declare a `row-key` field and column metadata:

```xml
<data-table id="usage" row-key="record_id" on-row-selected="usage_selected">
  <column key="date" label="Date" />
  <column key="requests" label="Requests" align="right" width="10" />
</data-table>
```

`label` overrides a column's literal body text; `align` accepts `left`, `center`, or `right`; and `width` is a positive native column width. Each heading has its own hover highlight. Click a column heading to sort ascending; click it again to reverse the order. The active heading uses a full-cell background and shows an `↑` or `↓` indicator, so leave room for it when using a fixed width. Runtime rows sort by their original values, so numeric fields remain numeric; seeded and manually added literal cells sort by their displayed values. Call `set_rows(records)` only after mounting. Every record must be a mapping with a non-empty string in the declared `row-key` field and every declared column key. TextUI validates the full batch before changing rows, renders `None` as an empty literal cell, and retains extra fields without adding columns. `get_record(row_key)` returns the read-only source record for the current batch and raises `KeyError` when absent. A refresh retains the active sort and cursor when its row key remains; otherwise the native cursor returns to the first cell. The [data example](../examples/data/app.ui) shows this runtime pattern beside seeded table and tree updates.
