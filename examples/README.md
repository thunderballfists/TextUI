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

Run `textui run examples/project/app.ui` from the repository root. The entry file loads `shell.tcss` and `controller.py`, then includes `views/form.ui`. The controller shows a greeting when the button is pressed and updates the clock once per second. Paths inside the project resolve from their declaring files, so the absolute entry path also works from another directory. See the [runtime guide](../docs/project-runtime.md).
