# Examples

The runnable examples use the public TextUI API from the `textui-markup` distribution. This checkout also contains unreleased authoring tools; examples and documentation on `main` follow the checkout rather than the last PyPI release. Follow the [checkout setup](../README.md#install-and-run) once, then run the commands below from the repository root. They use the installed project through Poetry rather than relying on a `textui` command on your shell's PATH.

For the full showcase on macOS or Linux, `./showcase` handles setup and launch automatically. Its absolute path also works from another directory; Ctrl+Q quits. Examples ship in the source distribution, not the library wheel.

## Choose an example

| Entry path | Demonstrates |
| --- | --- |
| `examples/editor.py` | Normal App composition and explicit event forwarding; run as `python -m examples.editor` |
| `examples/sample_markup.xml`, `examples/form.xml` | Static markup and the editor's form |
| `examples/project/app.ui` | Linked controller/styles, includes, navigation, split panes and timer |
| `examples/components/app.ui` | Local component properties and named slots |
| `examples/controls/app.ui` | Native form controls, tabs, disclosure and indicators |
| `examples/data/app.ui` | Runtime records, sorting, table columns and tree updates |
| `examples/list/app.ui` | Runtime-list record formatting, refresh and selection |
| `examples/log/app.ui` | Streamed transcript entries and log selection |
| `examples/bars/app.ui` | Left/center/right bar slots and controls |
| `examples/showcase/app.ui` | Combined feature showcase with density and border toggles |

Run any `.ui` entry through `uvx --python 3.12 --from poetry==2.4.3 poetry run python -m textui run ENTRY_PATH`. Project resources resolve relative to their declaring files; pass an absolute entry path when outside the repository. Component definitions and included view files are fragments, not runnable entry points. See [project validation](../docs/project-runtime.md#project-validation) to check an entry without opening its UI.

## Editor

Run the normal Textual host example:

```sh
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m examples.editor
```

Enter a name and press **Save**. The action updates the mounted `status` label. The example loads `form.xml` relative to its own module, so it also works when launched from another working directory. Press Ctrl+Q to quit.

## Sample markup

`sample_markup.xml` is a small static document showing six basic built-in widgets, IDs, classes, a direct `<style>` block, literal bracketed text, and typed boolean input. Load it from Python when experimenting with a custom host:

```python
from pathlib import Path

from textui import DocumentLoader, TextUI

document = DocumentLoader().from_file(Path("examples/sample_markup.xml"))
TextUI(document).run()
```

The sample has no actions, so it is useful for checking structure and styling without application callbacks. See the main [README](../README.md) for custom components and explicit event forwarding, and the [documentation index](../docs/README.md) for current references.
## Project runtime example

Run `uvx --python 3.12 --from poetry==2.4.3 poetry run python -m textui run examples/project/app.ui` from the repository root. The entry file loads `shell.tcss` and `controller.py`, then includes `views/form.ui`. The sidebar selects a page with the mouse or keyboard; the ☰ button hides or shows it, and the divider can be dragged or resized with arrow keys. The controller also shows a greeting and updates the clock once per second. Paths inside the project resolve from their declaring files, so the absolute entry path also works from another directory. See the [runtime guide](../docs/project-runtime.md).

Run `uvx --python 3.12 --from poetry==2.4.3 poetry run python -m textui run examples/controls/app.ui` to try native select, switch, text area, tabs, radio choices, collapsible content, progress bars, and rules. Their `on-*` actions update the feedback label. See the [controls guide](../docs/controls.md).

Run `uvx --python 3.12 --from poetry==2.4.3 poetry run python -m textui run examples/data/app.ui` to try an API-backed runtime table alongside a seeded native table and tree. The controller supplies local demonstration records; no network service is required. Select a row or node to update the feedback label, then press **Add job and file** to change both widgets from linked Python. See [tables and trees](../docs/controls.md#tables-and-trees).

## Reusable components

Run `uvx --python 3.12 --from poetry==2.4.3 poetry run python -m textui run examples/components/app.ui` to see a project-local `agent-card` component. The entry file imports the component, passes literal properties, and supplies a named action slot. See the [project runtime guide](../docs/project-runtime.md#reusable-components) for the authoring contract.

## Feature showcase

Run `./showcase` for a single application that exercises the full built-in surface. The sidebar is hideable and resizable, includes **Borders** (`Ctrl+B`) and **Quit** (`Ctrl+Q`) command buttons, and the right-justified top bar contains **Compact** (`Ctrl+D`) and Help controls. Compact toggles the framework's dense TCSS preset; Borders toggles rounded button outlines. Its pages cover imported components and includes, inputs and choices, tabs and indicators, API-backed runtime table records, seeded tables and trees, runtime lists, logs, modal screens, linked actions, and a repeating timer. It is the quickest manual smoke test after changing framework behavior.
