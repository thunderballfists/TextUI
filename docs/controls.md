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
