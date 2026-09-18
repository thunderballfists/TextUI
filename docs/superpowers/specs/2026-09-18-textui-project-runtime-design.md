# TextUI project runtime and workspace layout design

Date: 2026-09-18

Status: approved and implemented in the 0.3.0 branch.

## Purpose and sequence

TextUI 0.2.1 validates one XML document and binds it to one Textual App. The next work should make a `.ui` file a runnable project entry point with included markup, styles, and linked Python. A following milestone adds a mouse-driven navigation sidebar and resizable, hideable panes. Broad widget coverage comes after these paths prove the authoring model.

Keep Textual responsible for rendering, input, timers, workers, and the event loop. TextUI parses and links project files, registers deliberate components, and adapts the document to an App. It does not generate Python source or implement another scheduler. `textui run app.ui` is a small runtime command; loading and validation are its compiler-like phase. Existing `DocumentLoader`, `Document.bind`, and `TextUI(Document, actions=...)` remain usable without a project file.

Three approaches were considered: mapping every Textual widget immediately, making XML itself executable, and adding a project runtime over the current typed core. The project runtime is preferred because it preserves the HTML-like document while keeping native Textual behavior and explicit Python boundaries. Inline Python remains deferred.

## Project file and resource grammar

The entry file retains one attribute-free `<ui>` root. New directives are reserved and cannot be registered as components:

```xml
<ui>
  <style src="shell.tcss" />
  <script src="controller.py" />
  <button on-pressed="toggle_sidebar">☰</button>
  <include src="views/workspace.ui" />
</ui>
```

`<style src>` and `<script src>` are allowed only as direct children of the entry root. A sourced style has no inline content; existing inline `<style>` remains supported. Styles participate in document order, retain their own filename in diagnostics, and use Textual's TCSS parser. A script has exactly one `src`, no content, and is never embedded inline. Its Python is trusted application code, not sandboxed data.

`<include src>` may appear where a component child or top-level component is allowed. The included UTF-8 file has an attribute-free `<ui>` root containing component nodes and further includes; styles and scripts stay in the entry file for this milestone. The wrapper disappears when expanded. Relative paths resolve from the file containing the directive, including nested includes. Detect cycles using canonical paths and show the include chain. Apply document-wide duplicate-ID validation after expansion; retain each node's original filename and line. Missing files, malformed XML, invalid placement, and included content-policy violations raise contextual errors. No network URLs, globs, templates, or runtime reloading are added.

Resource discovery parses XML without executing Python. The runtime then creates an App, loads linked modules, and calls setup hooks in the App's load phase so they can register components before typed node validation and composition. It validates the expanded tree into a `Document` and binds it before mounting. Parsing a standalone document through the existing `DocumentLoader` does not implicitly import scripts.

## Linked Python and the `window` global

Each App binding executes each linked Python file once in its own module namespace, in entry-file order. The runtime injects a module-global `window` facade before executing that module; it never stores a process-wide current App. Two Apps started from the same `.ui` file receive different `window` objects and controller state. Normal Python imports inside the file remain normal Python imports.

`window.app` is the host Textual App. `window.registry` is available during setup for explicit `ComponentSpec` registration. `window.document` is the bound document after binding; mounted ID lookup works only at ready time or later. This facade exposes `after`, `every`, and `call_ui` as thin wrappers around native Textual APIs, but does not duplicate general App queries or rendering APIs. Timers may be created at ready time or later. Access outside the corresponding lifecycle phase raises a clear state error.

Linked files export actions with `@action`. The decorator marks a function for explicit registration under its Python name; it does not execute it. `on-pressed="toggle_sidebar"` still names an exact registered action. For low boilerplate, decorated actions may accept zero arguments and use `window`, or one `ActionContext` argument. Validate the signature once when linking, then adapt it to the existing one-context callback contract. Duplicate exported names across files or between linked and host-supplied actions are errors. Host-supplied actions remain supported. Undecorated functions are not callable from markup.

## Lifecycle and timers

Recognize at most one `on_setup`, `on_ready`, and `on_close` function per project, each synchronous or asynchronous and taking no arguments. `on_setup` runs after App/window creation but before component validation and binding; mounted widget lookup is unavailable. `on_ready` runs once after all document widgets are mounted, so `get_by_id` is valid. `on_close` runs once during orderly App shutdown and also after startup failure if setup completed. Hook failures retain source information and propagate; they are not logged and ignored. Native App subclasses retain their own Textual lifecycle hooks.

`@every(seconds)` marks a zero-argument periodic function. Validate that seconds is finite and positive. Register marked timers only after `on_ready` succeeds. `window.after(seconds, callback)` schedules one-shot work; `window.every(seconds, callback)` creates a dynamic repeating timer. Both return the native-style timer handle for pause/resume/stop. On close, stop runtime-owned timers and cancel active async workers. Thread cancellation remains cooperative.

Textual `set_interval`/`set_timer` schedule ticks. A short synchronous callback executes in the App's message context. An `async def` callback starts an App-owned async worker, keeping the message queue responsive. A synchronous blocking callback may opt into `@every(5, thread=True)` or `window.every(5, callback, thread=True)`; direct widget mutation from that thread is unsupported, and `window.call_ui(...)` marshals an update through `App.call_from_thread`. Repeating timers skip a tick while their previous invocation is active by default; they neither queue backlog nor overlap. Timer and worker failures retain the callback/source name and follow the App's error path. No additional event loop is created.

```python
from textui import action, every

def on_ready():
    window.app.title = "Workspace"

@action
def toggle_sidebar():
    pane = window.document.get_by_id("sidebar")
    pane.display = not pane.display

@every(5)
async def refresh_status():
    status = await fetch_status()
    window.document.get_by_id("status").update(status)
```

This is proposed API syntax, not a claim about the current package. An action or timer that performs long synchronous work must use an explicit thread worker; declaring a normal function does not make it nonblocking.

## Workspace layout milestone

After the runtime contract is tested, add a small navigation set rather than every Textual widget. A `<split direction="horizontal|vertical">` owns exactly two `<pane>` children, their minimum sizes, and a draggable divider. Textual mouse capture handles drag motion; keyboard resizing is also required for terminal users without a mouse. A collapsible pane uses Textual `display` so the other pane takes the freed space, and restores its previous size when shown. Clamp sizes on terminal resize. The split component owns its internal divider and publishes a resize/toggle message without exposing that divider as a document ID.

Add a mouse-selectable `<nav>` with `<nav-item>` children and a declared selected event. An action can switch a native `ContentSwitcher`-style content area using the selected target. Keep navigation targets explicit and validate missing targets before mounting. Included view files remain static until a separate multi-screen/reload design is approved. Do not turn the XML grammar into arbitrary HTML or duplicate Textual's screen/mode system.

## Acceptance and release boundaries

Test linked files from changed working directories; nested includes, cycles, duplicate IDs, file/source errors, style order, script ordering, duplicate actions, setup registration, independent App instances, and every lifecycle failure phase. Use Textual Pilot and controlled clocks/timers to test one-shot and periodic calls, async responsiveness, skipped overlap, explicit thread marshaling, cancellation, and clean shutdown. Test mouse drag, keyboard resizing, hide/show, minimum widths, terminal resize, and navigation selection in a headless App. Build and install the wheel in a clean environment and run the CLI from outside the checkout.

The existing six-widget API, strict XML parser, one binding per App, single-use composition, and trusted-document boundary remain. External Python execution is opt-in through the project runtime and clearly documented. Versioning, migration notes, and packaging for included resource files are part of implementation planning; no release version is chosen here.

References: [Textual timer API](https://textual.textualize.io/api/message_pump/), [timer handles](https://textual.textualize.io/api/timer/), [workers](https://textual.textualize.io/guide/workers/), [mouse input](https://textual.textualize.io/guide/input/), [App lifecycle](https://textual.textualize.io/guide/app/).
