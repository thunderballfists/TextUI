# Project runtime

Run a local project with `textui run path/to/app.ui` or `python -m textui run path/to/app.ui`. The entry file has one attribute-free `<ui>` root. Its direct children may contain inline `<style>`, `<style src="shell.tcss"/>`, and `<script src="controller.py"/>` alongside widgets. A `<script>` has only `src`, no embedded code. A sourced style also has no body.

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

Optional `on_setup`, `on_ready`, and `on_close` functions take no arguments and may be synchronous or asynchronous. Setup runs before component validation and binding; ready runs after mount; close runs once on shutdown and after a failed setup. `window.document` is available after binding, while ID lookup requires mounted widgets.

`window.after(seconds, callback)` schedules a one-shot callback and `window.every(seconds, callback, thread=False)` repeats it. `@every(seconds, thread=False)` starts a decorated timer after ready. All accept positive finite seconds and zero-argument callbacks; handles support `pause()`, `resume()`, and `stop()`. Async callbacks run as App workers; overlapping repeat ticks are skipped. Blocking synchronous work must opt into `thread=True`; use `window.call_ui(callback, *args, **kwargs)` from that thread for UI updates. Runtime timers stop when the App closes.

The low-level `DocumentLoader`, `Document.bind`, and `TextUI(Document, actions=...)` APIs remain available and do not execute linked files. The runnable [project example](../examples/project/app.ui) combines styles, a linked controller, an included view, an action, and a timer.

## Navigation and panes

## Modals

Declare a root-level `<modal id="pick" dismissable="true">` with normal widget content. An action may await `context.push_modal("pick")`; call `context.dismiss_modal(value)` from a modal action to return a value. Escape dismisses a dismissable modal with `None`; a non-dismissable modal ignores Escape. Focus returns to the prior screen after dismissal.

Use `<split direction="horizontal">` with exactly two `<pane>` children. A pane can set `size` for its initial width (or height in a vertical split) and `min-size` for its lower bound. Drag the divider with the mouse or focus it and press arrow keys. Setting a pane's Textual `display` property to `False` hides it; setting it back to `True` restores the stored size. The split publishes `resized` and `toggled` events to `on-resized` and `on-toggled` actions.

Use `<nav on-selected="show_page">` with `<nav-item target="home">Home</nav-item>` children. Each target must name a direct child of a `<content-switcher>`. The selected event carries `context.event.target`; an action can switch the native content area:

```python
@action
def show_page(context):
    window.document.get_by_id("content").current = context.event.target
```

The [project example](../examples/project/app.ui) combines a hideable sidebar, draggable split, navigation, and an included page. Included views remain static; the runtime does not add screen modes or hot reload.

## Runtime lists

Use `<list>` when a native selectable rail is populated after markup loads. `item-label` is a required Python-format pattern evaluated against each item mapping. The element has no child content; give it an ID and optionally bind `on-selected`.

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
