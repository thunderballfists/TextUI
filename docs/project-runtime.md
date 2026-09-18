# Project runtime

Run a local project with `textui run path/to/app.ui` or `python -m textui run path/to/app.ui`. The entry file has one attribute-free `<ui>` root. Its direct children may contain inline `<style>`, `<style src="shell.tcss"/>`, and `<script src="controller.py"/>` alongside widgets. A `<script>` has only `src`, no embedded code. A sourced style also has no body.

Use `<include src="views/workspace.ui"/>` wherever a widget child is allowed. Included files have their own `<ui>` root and may include other files, but may not declare scripts or styles. Relative paths are resolved from the file containing each directive, not from the shell's current directory. Cycles, missing resources, duplicate IDs, and invalid markup fail with source context. Includes are static; there is no network loading or reload.

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
