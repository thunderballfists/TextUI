# Project runtime

Run a local project with `textui run path/to/app.ui` or `python -m textui run path/to/app.ui`. The entry file has one attribute-free `<ui>` root. Its direct children may contain inline `<style>`, `<style src="shell.tcss"/>`, and `<script src="controller.py"/>` alongside widgets. A `<script>` has only `src`, no embedded code. A sourced style also has no body.

Use `<style preset="compact"/>` when an application needs denser native controls without maintaining a global stylesheet. It reduces horizontal padding and uses Textual's native compact state for buttons, text inputs, selects, text areas, and choice controls. Native compact controls remove their borders, so single-line inputs and selects use one terminal row. The default focus cue uses an accent background tint rather than an outline that could cover content. Compact buttons and choice controls keep Textual's own focus style; inputs, selects, and text areas receive a stronger tint. The preset participates in normal source order, so a later inline or sourced TCSS block can override any rule:

```xml
<ui>
  <style preset="compact" />
  <style>#save { padding: 0 2; }</style>
  <button id="save">Save</button>
</ui>
```

`compact` is opt-in; documents without it retain Textual's normal control density. Presets have no body and only accept the `preset` attribute.

Focus uses native `background-tint`, preserving button variants and author backgrounds. The default accent tint is 15%; compact inputs, selects, and text areas use 25%. Adjust it in application TCSS, after presets, with a focused selector:

```css
Button:focus, Input:focus, Select:focus, TextArea:focus,
DataTable:focus, Tree:focus, RuntimeList:focus {
    background-tint: $accent 6%;
}
```

Use `background-tint: transparent` to disable TextUI's tint for selected controls while retaining their other native focus styling. Changing only `background` does not disable the tint.

A linked controller can switch any declared preset while the application runs. The method returns its new enabled state and reapplies the host stylesheet plus all active document blocks in their original order:

```python
@command(label="Compact", shortcut="ctrl+d")
def toggle_compact():
    enabled = window.document.toggle_style_preset("compact")
    window.document.get_by_id("feedback").update(
        "Compact controls on" if enabled else "Compact controls off"
    )
```

The preset must be declared in the entry document before it can be toggled. Inline styles and later document TCSS continue to override it after each switch.

Use `<style preset="borders"/>` for rounded Unicode button outlines. It is independent of `compact`; declare it after `compact` when both are active, so its real borders override the borderless native compact button state and reserve enough rows for the label. `window.document.toggle_style_preset("borders")` switches the outlines at runtime. Idle buttons use `round` borders, hover keeps the rounded outline, and focused buttons use a `double` border.

Use `<include src="views/workspace.ui"/>` wherever a widget child is allowed. Included files have their own `<ui>` root and may include other files, but may not declare scripts or styles. Relative paths are resolved from the file containing each directive, not from the shell's current directory. Cycles, missing resources, duplicate IDs, and invalid markup fail with source context. Includes are static; there is no network loading or reload.

## Project validation

Use `python -m textui check /absolute/path/app.ui` with the project's installed interpreter. From a checkout, follow [setup](../README.md#install-and-run), then run:

```sh
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m textui check examples/showcase/app.ui
```

The check discovers linked resources, executes controller scripts in entry order, awaits `on_setup`, lowers components/includes, validates action and command bindings, and constructs declared widget trees. Dormant modal contents and their inline styles are checked too. Document styles use native TCSS parsing and the default host theme variables. The app and widgets are never mounted; no ready/resize hooks, event dispatch or declared timers run.

`on_close` runs once when setup has begun, on success or failure. If cleanup also fails, the original validation failure remains primary and the cleanup diagnostic is reported alongside it. During `check`, script loading failures before setup do not run close hooks; native `run` shutdown may close already-loaded controllers in that case. Setup and close hooks must tolerate an unmounted document; mounted lookup is unavailable. Scripts, hooks and factories are trusted Python and can perform arbitrary side effects. This is not static-only validation or an untrusted-input sandbox.

A successful check covers declarations and construction, not custom widget `compose()`/mount hooks, widget default TCSS, computed layout or interactive behavior. Exercise those with native Textual `run_test()` and Pilot or by launching the app.

Expected TextUI errors print source context to stderr without a traceback. `--debug` before or after `check`/`run` includes their original exception chains. Unexpected exceptions always retain a traceback. Exit statuses are 0 (success), 1 (project error), 2 (usage error), 3 (unexpected failure), and 130 (keyboard interruption). `run` preserves explicit application exit codes and restores the terminal before reporting captured runtime errors.

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

Hosts can pass application inputs directly: `ProjectApp(source, context={"account": "demo"})` exposes the same object as `window.context` during script loading and every hook. `window.context` cannot be reassigned, though a mutable object passed by the host remains mutable. Its default is `None`; each App receives its own supplied reference.

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

Actions and commands can opt into target lifecycle state, for synchronous or asynchronous work. Set `target` to a declared widget ID to add `-loading` while work runs and `-error` with a readable `textui_error` value when it fails. A shared target stays loading until every active invocation finishes; synchronous completion also releases its ownership. Starting new work clears previous errors, and only the newest invocation may publish a target error. An older failure still reaches the normal source-located error handler.

Set `supersede=True` to cancel earlier invocations of the same operation and target, including when the replacement completes synchronously. Other operations sharing the target continue. `context.target` is the mounted target and `context.cancelled` reports cancellation, including for untargeted actions. Cancellation is cooperative: callbacks that suppress it and threads may still perform their own side effects.

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

Both convenience Apps close their document when exit begins, cancelling all owned asynchronous actions and commands, including untargeted work and queued shortcut wrappers. Repeated `document.close()` calls are harmless. A closed document ignores queued `dispatch()` messages, rejects direct `invoke_command()` calls with `DocumentStateError`, and makes `start_command()` a no-op. Normal Textual hosts must call their bound document's `close()` when shutdown begins and on unmount; it requests cancellation without waiting for user callbacks.

Optional `on_resize(width, height)` runs after Textual delivers a terminal resize to the active screen and refreshes its layout. Width and height are terminal cells; mounted widget sizes can be read inside the hook. It accepts a synchronous or asynchronous function, runs only while the project is ready, and stops when exit begins. TextUI drops stale and duplicate sizes; Textual may also coalesce rapid terminal resizes, so paint from the dimensions supplied rather than counting raw resize events:

```python
def on_resize(width, height):
    title = window.document.get_by_id("title")
    title.update(f"Workspace ({width} × {height})")
```

`window.after(seconds, callback)` schedules a one-shot callback and `window.every(seconds, callback, thread=False)` repeats it. `@every(seconds, thread=False)` starts a decorated timer after ready. All accept positive finite seconds and zero-argument callbacks; handles support `pause()`, `resume()`, and `stop()`. Async callbacks run as App workers; overlapping repeat ticks are skipped. Blocking synchronous work must opt into `thread=True`; use `window.call_ui(callback, *args, **kwargs)` from that thread for UI updates. Runtime timers stop when the App closes.

The low-level `DocumentLoader`, `Document.bind`, and `TextUI(Document, actions=...)` APIs remain available and do not execute linked files. The runnable [project example](../examples/project/app.ui) combines styles, a linked controller, an included view, an action, and a timer.

## Navigation and panes

## Modals

Declare a root-level `<modal id="pick" dismissable="true">` with normal widget content. `context.push_modal("pick")` returns a dismissal future with a `.mounted` awaitable. Await `.mounted` before looking up or populating runtime modal widgets; await the result itself only when waiting for dismissal. Call `context.dismiss_modal(value)` from a modal action to return a value. Escape dismisses a dismissable modal with `None`; a non-dismissable modal ignores Escape. Focus returns to the prior screen after dismissal.

Each declared modal can be active once. Calling `push_modal("pick")` again before it closes raises `DocumentStateError`; distinct modal declarations may nest. A completed `push_modal()` await means the old modal screen has unmounted, so the same declaration can open again immediately. Dismissal removes the modal's public IDs and all of its event bindings, including anonymous and component-private controls. Cancelling the future returned by `push_modal()` does not dismiss its screen; later dismissal still releases its bindings.

Use `<split direction="horizontal">` with exactly two `<pane>` children. A pane can set `size` for its initial width (or height in a vertical split) and `min-size` for its lower bound. Drag the divider with the mouse or focus it and press arrow keys. Setting a pane's Textual `display` property to `False` hides it; setting it back to `True` restores the stored size. The split publishes `resized` and `toggled` events to `on-resized` and `on-toggled` actions.

A split fills the remaining height of its structural parent by default, so a `<vertical>` shell can place a `<header>`, split body, and `<status-bar>` without hand-written height rules. Set an explicit height only when the body is intentionally fixed. A `<tabbed-content>`, its content switcher and each `<tab-pane>` fill the remaining height the same way, so a `1fr` widget inside a pane is as tall as the pane; override the height in TCSS for content-sized tabs.

Use `<nav on-selected="show_page">` with `<nav-item target="home">Home</nav-item>` children. Each target must name a direct child of a `<content-switcher>`. The selected event carries `context.event.target`; an action can switch the native content area:

```python
@action
def show_page(context):
    window.document.get_by_id("content").current = context.event.target
```

The [project example](../examples/project/app.ui) combines a hideable sidebar, draggable split, navigation, and an included page. Included views remain static; the runtime does not add screen modes or hot reload.

## Header and status-bar controls

`header` and `status-bar` accept optional `left`, `center`, and `right` slots. Each slot accepts ordinary widgets, including buttons and labels. The edge slots share the available width, the center stays centered, and the right slot right-justifies its contents. When the center slot is empty there is nothing to keep centered, so the right slot takes the width its contents need and the left slot keeps the rest.

```xml
<header>
  <left><button on-pressed="toggle_sidebar">☰</button></left>
  <center><label>Workspace</label></center>
  <right><label id="clock">Starting…</label><button on-pressed="open_help">Help</button></right>
</header>
```

The [showcase](../examples/showcase/app.ui) places its Help control in the top-right slot and its Quit command below the sidebar navigation.

Bars also accept a TextUI gradient background through an ID selector in a TCSS block. Use an explicit degree angle and two or more literal Textual colors. `0deg` runs horizontally across the bar; `90deg` runs vertically. TextUI renders the gradient beneath the bar's slot widgets; gradients currently apply only to `header` and `status-bar` surfaces. A later matching solid background or an opaque slot background covers the gradient, including label text; changing classes at runtime uses the current TCSS winner.

```tcss
#top-bar { background: linear-gradient(0deg, #004e92, #00a8e8, #5614b0); }
```

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

`set_rows()` accepts a complete iterable of mappings and changes no rows until all records validate. Each record needs every declared column. A declared `row-key` must be a unique, non-empty string and preserves the cursor across refreshes; duplicate keys identify the table and source attribute in the error. Without `row-key`, TextUI uses zero-based positional keys for the replacement batch. `None` cells display empty, while extra record fields remain accessible through read-only `get_record()` results. Each heading highlights independently under the mouse. Click a column heading to sort ascending and click again to reverse it; the active header uses a full-cell background and shows an `↑` or `↓` indicator. Runtime records use their original values so numbers retain numeric order, and later `set_rows()` refreshes retain the active sort. Refreshing keeps the selected row and column when its key remains; an absent key or an empty batch uses the native first-cell fallback. Static seed rows and direct native `add_row()` calls continue to work without `row-key`, with displayed literal values used for header sorting.

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

Transcript mouse selections survive appends that keep selected rows in place. Eviction, clearing, and streamed-entry rewrites clear the affected log selection so copying cannot return unrelated replacement text.

## Selection and clipboard

Copying on selection is opt-in. `<log on-selection-ended="copy_selection"/>` emits a completed nonempty pointer selection, including release outside the log. Its event exposes `.log`, `.text`, and native `.selection` coordinates; content updates do not emit selection completion.

```python
@action
async def copy_selection(context):
    backend = await window.copy(context.event.text)
```

`window.copy(text)` is available while ready. Normal Textual hosts can instead import `copy_to_clipboard` from `textui` and call `await copy_to_clipboard(app, text)`. The helper asynchronously tries `pbcopy` on macOS, `clip` on Windows, or Wayland/X11 tools on Linux, with Unicode stdin and a two-second timeout per candidate. It also sends Textual's OSC 52 transport for the terminal's clipboard. The return value names the successful native tool, or `osc52` if only the terminal transport was sent; it does not confirm terminal acceptance. Clipboard text never becomes a shell command. Textual's own copy shortcuts remain unchanged. The showcase demonstrates this opt-in action.

Document tab layout defaults apply in normal Textual Apps through `Document.bind()` as well as `TextUI` and `ProjectApp`. Host-owned native tab widgets are unaffected; author TCSS can override document tab and pane heights.
