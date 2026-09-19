# Examples

The examples use the public TextUI 0.2 API and should be run from the repository root after installing the project.

## Editor

Run the normal Textual host example:

```sh
python -m examples.editor
```

Enter a name and press **Save**. The action updates the mounted `status` label. The example loads `form.xml` relative to its own module, so it also works when launched from another working directory. Press Ctrl+Q to quit.

## Sample markup

`sample_markup.xml` is a small static document showing the six built-in widgets, IDs, classes, a direct `<style>` block, literal bracketed text, and typed boolean input. Load it from Python when experimenting with a custom host:

```python
from pathlib import Path

from textui import DocumentLoader, TextUI

document = DocumentLoader().from_file(Path("examples/sample_markup.xml"))
TextUI(document).run()
```

The sample has no actions, so it is useful for checking structure and styling without application callbacks. See the main [README](../README.md) for custom components and explicit event forwarding.
# Project runtime example

Run `textui run examples/project/app.ui` from the repository root. The entry file loads `shell.tcss` and `controller.py`, then includes `views/form.ui`. The sidebar selects a page with the mouse or keyboard; the ☰ button hides or shows it, and the divider can be dragged or resized with arrow keys. The controller also shows a greeting and updates the clock once per second. Paths inside the project resolve from their declaring files, so the absolute entry path also works from another directory. See the [runtime guide](../docs/project-runtime.md).

Run `textui run examples/controls/app.ui` to try native select, switch, text area, tabs, radio choices, collapsible content, progress bars, and rules. Their `on-*` actions update the feedback label. See the [controls guide](../docs/controls.md).

Run `textui run examples/data/app.ui` to try a native table and tree. Select a row or node to update the feedback label, then press **Add job and file** to change both widgets from linked Python. See [tables and trees](../docs/controls.md#tables-and-trees).

## Reusable components

Run `textui run examples/components/app.ui` to see a project-local `agent-card` component. The entry file imports the component, passes literal properties, and supplies a named action slot. See the [project runtime guide](../docs/project-runtime.md#reusable-components) for the authoring contract.

## Feature showcase

Run `textui run examples/showcase/app.ui` for a single application that exercises the full built-in surface. The sidebar is hideable and resizable; its pages cover imported components and includes, inputs and choices, tabs and indicators, tables and trees, runtime lists, logs, modal screens, linked actions, and a repeating timer. It is the quickest manual smoke test after changing framework behavior.
