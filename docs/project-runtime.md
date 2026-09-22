# Project runtime

Run a local project with `textui run path/to/app.ui` or `python -m textui run path/to/app.ui`. The entry file has one attribute-free `<ui>` root. Its direct children may contain inline `<style>`, `<style src="shell.tcss"/>`, and `<script src="controller.py"/>` alongside widgets. A `<script>` has only `src`, no embedded code. A sourced style also has no body.

Use `<style preset="compact"/>` when an application needs denser native controls without maintaining a global stylesheet. It reduces horizontal padding and uses Textual's native compact state for buttons, text inputs, selects, text areas, and choice controls. Native compact controls remove their borders, so single-line inputs and selects use one terminal row. The preset participates in normal source order, so a later inline or sourced TCSS block can override any rule:

```xml
<ui>
  <style preset="compact" />
  <style>#save { padding: 0 2; }</style>
  <button id="save">Save</button>
</ui>
```

`compact` is opt-in; documents without it retain Textual's normal control density. Presets have no body and only accept the `preset` attribute. A linked controller can switch any declared preset while the application runs. The method returns its new enabled state and reapplies the host stylesheet plus all active document blocks in their original order:

```python
@command(label="Compact", shortcut="ctrl+d")
def toggle_compact():
    enabled = window.document.toggle_style_preset("compact")
    window.document.get_by_id("feedback").update(
        "Compact controls on" if enabled else "Compact controls off"
    )
```

The preset must be declared in the entry document before it can be toggled. Inline styles and later document TCSS continue to override it after each switch.

Use `<style preset="borders"/>` for rounded Unicode button outlines. It is independent of `compact`; declare it after `compact` when both are active, so its explicit outline overrides the borderless native compact button state. `window.document.toggle_style_preset("borders")` switches the outlines at runtime. Idle buttons use `round` borders, hover keeps the rounded outline, and focused buttons use a `double` border.

Use `<include src="views/workspace.ui"/>` wherever a widget child is allowed. Included files have their own `<ui>` root and may include other files, but may not declare scripts or styles. Relative paths are resolved from the file containing each directive, not from the shell's current directory. Cycles, missing resources, duplicate IDs, and invalid markup fail with source context. Includes are static; there is no network loading or reload.

## Reusable components

Import reusable markup directly below the entry `<ui>` root. The alias is a project-local lowercase kebab-case widget name:

```xml
<ui>
  <component src="components/agent-card.ui" as="agent-card" />
  <agent-card id="alpha" name="Alpha">
    <slot name="actions"><button on-pressed="open_alpha">Open</button></slot>
  </agent-card>
</ui>
```

The imported file has a `<component>` root, optional properties, and one widget root:

```xml
<component>
  <props><prop name="name" required="true" /></props>
  <vertical class="agent-card"><label>{name}</label><slot name="actions"><button>Details</button></slot></vertical>
</component>
```

Properties are literal strings: required values must be supplied, defaults fill omissions, and unknown properties fail. `{name}` substitutes only the declared property; it never evaluates Python. A caller's named slot replaces the matching template slot, while omitted slots keep fallback content. The instance `id`, classes, style, disabled state, and `on-*` event bindings apply to the rendered root. Template IDs receive unique private prefixes, so controller code addresses the public instance ID. Components may import other explicitly declared components. Component files cannot declare scripts or styles; entry-document TCSS styles their widgets. The runnable [component example](../examples/components/app.ui) shows the complete layout.

Linked Python is trusted application code. Each App executes each linked file once in its own namespace, with a module-global `window` available before the script executes. Use `window.app` for the host Textual App, `window.registry` to register components during `on_setup`, and `window.document.get_by_id("status")` after widgets mount. Ordinary imports work as normal Python imports. No Python is embedded in markup.

```python
from textui import action, every

def on_ready():
    window.app.title = "Workspace"

@action
def save():
    window.document.get_by_id("status").update("Saved")

@every(5)
async def refresh():
    result = await fetch_status()
    window.document.get_by_id("status").update(result)
```

An `@action` function is exposed under its Python name and may take zero arguments or one `ActionContext`; undecorated functions are private to the script. `on-pressed="save"` refers to that exact name. Duplicate action names, including collisions with host-supplied actions, are errors.

Async data actions can opt into target lifecycle state. Set `target` to a declared widget ID to add `-loading` while work runs and `-error` with a readable `textui_error` value when it fails. Set `supersede=True` to cancel an earlier invocation of the same action and target; shutdown also cancels active lifecycle work. `context.target` is the mounted target and `context.cancelled` reports cancellation.

```python
@action(target="results", supersede=True)
async def refresh(context):
    await context.target.set_items(await fetch_results())
```

## Shared commands and shortcuts

Use `@command` for a zero-argument controller operation shared by a command control and an optional shortcut. Command bodies use the existing `window` global, so the same function runs from a pointer click or keyboard binding without event-specific boilerplate.

```python
from textui import command

@command(label="Quit", shortcut="ctrl+q", description="Exit the application")
def quit_app():
    window.app.exit()
```

Render it with a self-labeling control:

```xml
<command-button id="quit" command="quit_app" variant="error" />
```

`label` defaults to the function name in title case, so `open_help` becomes **Open Help**. The shortcut description defaults to the label and appears in Textual binding help. `enabled=False` renders each command button disabled and ignores its shortcut. Commands also accept the same optional `target` and `supersede` lifecycle arguments as actions. Command names must be unique across linked scripts, command functions take no parameters, and every command button must reference a declared command. A command is also available to an ordinary `on-*` directive by its function name; use `@action` when the callback needs an `ActionContext` event.

Optional `on_setup`, `on_ready`, and `on_close` functions take no arguments and may be synchronous or asynchronous. Setup runs before component validation and binding; ready runs after mount; close runs once on shutdown and after a failed setup. `window.document` is available after binding, while ID lookup requires mounted widgets.

`window.after(seconds, callback)` schedules a one-shot callback and `window.every(seconds, callback, thread=False)` repeats it. `@every(seconds, thread=False)` starts a decorated timer after ready. All accept positive finite seconds and zero-argument callbacks; handles support `pause()`, `resume()`, and `stop()`. Async callbacks run as App workers; overlapping repeat ticks are skipped. Blocking synchronous work must opt into `thread=True`; use `window.call_ui(callback, *args, **kwargs)` from that thread for UI updates. Runtime timers stop when the App closes.

The low-level `DocumentLoader`, `Document.bind`, and `TextUI(Document, actions=...)` APIs remain available and do not execute linked files. The runnable [project example](../examples/project/app.ui) combines styles, a linked controller, an included view, an action, and a timer.

## Navigation and panes

## Modals

Declare a root-level `<modal id="pick" dismissable="true">` with normal widget content. `context.push_modal("pick")` returns a dismissal future with a `.mounted` awaitable. Await `.mounted` before looking up or populating runtime modal widgets; await the result itself only when waiting for dismissal. Call `context.dismiss_modal(value)` from a modal action to return a value. Escape dismisses a dismissable modal with `None`; a non-dismissable modal ignores Escape. Focus returns to the prior screen after dismissal.

Each declared modal can be active once. Calling `push_modal("pick")` again before it closes raises `DocumentStateError`; distinct modal declarations may nest. A completed `push_modal()` await means the old modal screen has unmounted, so the same declaration can open again immediately. Dismissal removes the modal's public IDs and all of its event bindings, including anonymous and component-private controls. Cancelling the future returned by `push_modal()` does not dismiss its screen; later dismissal still releases its bindings.

Use `<split direction="horizontal">` with exactly two `<pane>` children. A pane can set `size` for its initial width (or height in a vertical split) and `min-size` for its lower bound. Drag the divider with the mouse or focus it and press arrow keys. Setting a pane's Textual `display` property to `False` hides it; setting it back to `True` restores the stored size. The split publishes `resized` and `toggled` events to `on-resized` and `on-toggled` actions.

Use `<nav on-selected="show_page">` with `<nav-item target="home">Home</nav-item>` children. Each target must name a direct child of a `<content-switcher>`. The selected event carries `context.event.target`; an action can switch the native content area:

```python
@action
def show_page(context):
    window.document.get_by_id("content").current = context.event.target
```

The [project example](../examples/project/app.ui) combines a hideable sidebar, draggable split, navigation, and an included page. Included views remain static; the runtime does not add screen modes or hot reload.

## Header and status-bar controls

`header` and `status-bar` accept optional `left`, `center`, and `right` slots. Each slot accepts ordinary widgets, including buttons and labels. The edge slots share the available width, the center stays centered, and the right slot right-justifies its contents.

```xml
<header>
  <left><button on-pressed="toggle_sidebar">☰</button></left>
  <center><label>Workspace</label></center>
  <right><label id="clock">Starting…</label><button on-pressed="open_help">Help</button></right>
</header>
```

The [showcase](../examples/showcase/app.ui) places its Help control in the top-right slot and its Quit command below the sidebar navigation.

## Runtime tables

Use a native table for structured records from a linked controller. Declare the record identity with `row-key`, then give each visible field a `column`. The optional `label`, `align="left|center|right"`, and positive `width` attributes control the native column heading and layout.

```xml
<data-table id="usage" row-key="record_id" on-row-selected="usage_selected">
  <column key="date" label="Date" />
  <column key="requests" label="Requests" align="right" width="10" />
</data-table>
```

```python
@action
def refresh_usage():
    window.document.get_by_id("usage").set_rows(records)

@action
def usage_selected(context):
    record = window.document.get_by_id("usage").get_record(context.event.row_key.value)
```

`set_rows()` accepts a complete iterable of mappings and changes no rows until all records validate. Each record needs every declared column and a unique, non-empty string record key. `None` cells display empty, while extra record fields remain accessible through read-only `get_record()` results. Each heading highlights independently under the mouse. Click a column heading to sort ascending and click again to reverse it; the active header uses a full-cell background and shows an `↑` or `↓` indicator. Runtime records use their original values so numbers retain numeric order, and later `set_rows()` refreshes retain the active sort. Refreshing keeps the selected row and column when its key remains; an absent key or an empty batch uses the native first-cell fallback. Static seed rows and direct native `add_row()` calls continue to work without `row-key`, with displayed literal values used for header sorting.

## Runtime lists

Use `<list>` when a native selectable rail is populated after markup loads. `item-label` is a required Python-format pattern evaluated against each item mapping. Every replacement field must be a direct mapping key: `{name}` and `{count:03d}` are valid, while `{agent.name}` and `{items[0]}` are rejected. The element has no child content; give it an ID and optionally bind `on-selected`.

```xml
<list id="agents" item-label="{name}" on-selected="select_agent" />
```

`set_items()` replaces the rows, so await it from an asynchronous action or lifecycle hook. Rows must be mappings that satisfy the label pattern. It resets `selected` to `None`, highlights the first row for keyboard navigation, and preserves native arrow-key, Enter, and pointer behavior. The selected event provides the original mapping as `context.event.item` and its zero-based position as `context.event.index`.

```python
async def on_ready():
    await window.document.get_by_id("agents").set_items(agents)

@action
def select_agent(context):
    agent = context.event.item
    window.document.get_by_id("heading").update(agent["name"])
```

The [runtime list example](../examples/list/app.ui) uses this pattern for a master-detail rail.
