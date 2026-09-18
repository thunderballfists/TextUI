# TextUI

TextUI turns strict XML documents into native [Textual](https://textual.textualize.io/) widgets. XML describes structure, TCSS controls appearance, and explicitly registered Python actions handle behavior. Textual owns layout, rendering, messages, and the application lifecycle. The current development branch also has a local `.ui` project runtime with linked files.

This is a breaking pre-1.0 reboot. See the [migration guide](docs/migration.md) for changes from 0.1, the [changelog](CHANGELOG.md) for release history, and the [implemented design](docs/superpowers/specs/2026-09-17-textui-core-design.md) for the complete contract.

## Install and run

Python `>=3.11,<4` is required; the release matrix covers 3.11, 3.12, and 3.14. Core dependencies are Textual `>=8.2.8,<9` and lxml `>=6.1.3,<7`. Core installation does not require Pillow or textual-imageview; image components are a future extension.

From a checkout:

```sh
python -m pip install .
textui run examples/project/app.ui
python -m examples.editor
```

The project example demonstrates a linked Python controller, local TCSS, an included view, an action, and a timer; see the [project runtime guide](docs/project-runtime.md). The separate editor is a small form demonstrating a Save action that updates a status label; it does not write a file. Press Ctrl+Q to quit. Its XML path is relative to the example module, independent of the working directory. See [examples/README.md](examples/README.md) for the static sample document. Examples are included in the source distribution, not the installed library wheel.

A self-contained application:

```python
from textual.content import Content
from textui import ActionContext, DocumentLoader, TextUI


def greet(context: ActionContext) -> None:
    name = context.document.get_by_id("name").value
    context.document.get_by_id("status").update(Content(f"Hello, {name}!"))


document = DocumentLoader().from_string("""
<ui>
  <vertical>
    <input id="name" placeholder="Your name" />
    <button on-pressed="greet">Greet</button>
    <label id="status">Ready</label>
  </vertical>
</ui>
""")
app = TextUI(document, actions={"greet": greet})
app.run()
```

Use `DocumentLoader().from_file("form.xml")` for UTF-8 files. `from_string` always receives markup and never guesses a filename. Errors retain source and element context and, where available, the original exception as their cause.

## Markup

Require one attribute-free `<ui>` root. Names are lowercase kebab-case; XML is parsed strictly. Comments are allowed. The project runtime accepts only linked scripts declared at the entry root; the standalone `DocumentLoader` does not load scripts. Namespaces, DTDs, entities, unknown tags/attributes/events, and duplicate IDs are rejected. Text in leaf widgets is literal, with whitespace collapsed; nested markup in leaves and mixed text/widget content are unsupported.

| Tag | Content | Attributes beyond common attributes | Events |
| --- | --- | --- | --- |
| `vertical`, `horizontal` | Widgets | None | None |
| `label` | Text | None | None |
| `button` | Text | `variant`: default, primary, success, warning, error | `pressed` |
| `input` | None | `value`, `placeholder`, `password`, positive `max-length` | `changed`, `submitted` |
| `checkbox` | Text | Boolean `value` | `changed` |

All widgets accept `id`, whitespace-separated `class`, `disabled`, and literal `style`. Boolean values must be `true` or `false`. An event attribute such as `on-pressed="save_document"` names an exact exposed action key; it cannot contain expressions, arguments, or dotted paths. Callbacks take one `ActionContext` containing `event`, `widget`, `app`, and the bound `document`. Both synchronous and asynchronous callbacks work. Initialization events follow Textual's normal behavior. Actions do not automatically stop bubbling or prevent default behavior; errors propagate as `ActionExecutionError` with the original cause.

## Integrate with a normal App

Bind after `App.__init__` and before the App runs. Compose the binding through the normal Textual hook, then explicitly forward native messages. [The runnable editor](examples/editor.py) implements this complete pattern:

```python
from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Button, Checkbox, Input
from textui import Document, DocumentLoader


class Host(App):
    def __init__(self, document: Document) -> None:
        super().__init__()
        self.document = document.bind(self, actions={})

    def compose(self) -> ComposeResult:
        yield from self.document.compose()

    @on(Button.Pressed)
    @on(Input.Changed)
    @on(Input.Submitted)
    @on(Checkbox.Changed)
    async def forward_document_message(self, event) -> None:
        await self.document.dispatch(event)


Host(DocumentLoader().from_string("<ui><label>Hello</label></ui>")).run()
```

`TextUI` supplies those four handlers for convenience. `get_by_id` returns only widgets with declared document IDs and requires them to be mounted. Use native `app.query()` / `app.query_one()` for general selectors. A `Document` can be reused in independent Apps; each binding constructs fresh widgets. There is one binding per App and a single composition attempt per binding. Recomposition, remounting, document replacement, and transparent attachment to a running App are unsupported.

## Add components and events

`ComponentRegistry()` starts empty. To extend the built-ins, use `default_component_registry` from `textui.widgets.builtin_widgets`, then register additional immutable `ComponentSpec` definitions. Construct `DocumentLoader(registry)` after registration; the loader snapshots the registry.

A factory receives `BuildContext(attributes, text, children, location)` and must return a fresh, unmounted Textual `Widget`. Attributes have already been converted by the registered `AttributeSpec` converters; the common layer applies IDs, classes, disabled state, and inline styles. Factories for containers attach `context.children` exactly once.

For example, a typed custom label:

```python
from textual.widgets import Label
from textui import AttributeSpec, BuildContext, ComponentSpec, DocumentLoader, TextUI, integer
from textui.widgets.builtin_widgets import default_component_registry


def count_label(context: BuildContext) -> Label:
    return Label(f"Count: {context.attributes['count']}", markup=False)


registry = default_component_registry()
registry.register(ComponentSpec(
    tag="count-label",
    factory=count_label,
    attributes={"count": AttributeSpec(integer(minimum=0), default=0)},
))
loader = DocumentLoader(registry)
TextUI(loader.from_string('<ui><count-label count="3" /></ui>')).run()
```

Declare custom events with `events={"updated": EventSpec(CustomMessage, lambda event: event.widget)}` on the component spec, using the message's actual source-widget property. The host must also implement `@on(CustomMessage)` and `await self.document.dispatch(event)`. Subclassing `TextUI` is sufficient. Dispatch matches the **exact registered message type** and originating widget identity; no handlers are discovered automatically. See the [tested custom component and message example](tests/test_extensions.py).

## Styles and trust

Embedded `<style>` blocks use native TCSS and are App-wide. The project runtime also accepts `<style src="file.tcss"/>` at the entry root. Styles follow host `CSS` / `CSS_PATH` author rules and retain document block order at equal specificity and importance. Native specificity, `!important`, widget defaults, and inline priority still apply. Inline declarations use native `set_styles`; they may contain literal values but not variable references. Put variables in a `<style>` block or host TCSS. Theme variables are available, while variables declared within one embedded block are local to that source. Standalone hosts may use `CSS_PATH` for external styles.

Styles are validated before document widgets are yielded or document styles are installed. Native validation failures are reported; declarations are never silently removed. Stylesheet integration is isolated in `textui/styling.py` and must be checked when upgrading Textual.

Documents, linked Python, actions, converters, and factories must be developer-controlled. This is **not an untrusted-input sandbox**. No inline scripting, expressions, templates, automatic data binding, hot reload, or browser HTML compatibility is provided.

## Development

Use Poetry 2.4.3 in an isolated tool environment:

```sh
uvx --python 3.12 --from poetry==2.4.3 poetry install --with test
uvx --python 3.12 --from poetry==2.4.3 poetry check --lock
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest -q
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m examples.editor
uvx --python 3.12 --from poetry==2.4.3 poetry build
```

Tests run headlessly and include actual Pilot interactions, computed styles, custom events, and the example form. CI runs Python 3.11/3.12/3.14, builds the distribution, and installs each wheel into a clean environment for an image-free headless smoke test.

TextUI is released under the [MIT License](LICENSE).
