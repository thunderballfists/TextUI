# TextUI

TextUI 0.7 turns declarative, HTML-like markup into native [Textual](https://textual.textualize.io/) widgets. Tags describe structure, TCSS controls appearance, and explicitly registered Python actions handle behavior. Textual owns layout, rendering, messages, and the application lifecycle. A local `.ui` project runtime loads linked files. The distribution is named **`textui-markup`**; Python imports and the command remain **`textui`**.

This is a breaking pre-1.0 reboot. See the [migration guide](https://github.com/thunderballfists/TextUI/blob/main/docs/migration.md) for changes from 0.1, the [changelog](https://github.com/thunderballfists/TextUI/blob/main/CHANGELOG.md) for release history, and the [implemented design](https://github.com/thunderballfists/TextUI/blob/main/docs/superpowers/specs/2026-09-17-textui-core-design.md) for the complete contract.

The [roadmap](https://github.com/thunderballfists/TextUI/blob/main/docs/roadmap.md) records current priorities, completion gates, and the reliability implementation plan. Historical library comparisons remain in the [extension triage](https://github.com/thunderballfists/TextUI/blob/main/docs/2026-09-19-extension-triage.md).

## Install and run

Python `>=3.11,<4` is required; the release matrix covers 3.11, 3.12, and 3.14. Core dependencies are Textual `>=8.2.8,<9` and lxml `>=6.1.3,<7`. Core installation does not require Pillow or textual-imageview; image components are a future extension.

Install the library into a fresh virtual environment:

```sh
python -m pip install textui-markup
python -c "import textui"
python -m textui run /absolute/path/app.ui
```

The PyPI project named `textui` is unrelated. Both distributions use the `textui` import package, so installing them together causes collisions. For an existing Git installation, follow the [distribution migration](https://github.com/thunderballfists/TextUI/blob/main/docs/migration.md#distribution-name-in-07). For development and the bundled examples, use the checkout instructions below. Maintainers: see the [release guide](https://github.com/thunderballfists/TextUI/blob/main/docs/releases.md).

For a checkout on macOS or Linux, install [uv](https://docs.astral.sh/uv/getting-started/installation/) once, then run:

```sh
./showcase
```

The launcher uses Python 3.12 and isolated Poetry 2.4.3, installs the locked project and test dependencies, and runs `python -m textui`. Its Poetry-managed environment lives in Poetry's cache, outside the checkout. No shell activation or globally available `textui` command is needed. The first run may download Python, Poetry and dependencies; later runs check the locked install before opening the app. Ctrl+Q quits.

From another directory, use the launcher's absolute path, for example:

```sh
/Users/abeihl/Development/TextUI/showcase
```

For other examples or development commands, use the same environment policy from the repository root:

```sh
unset VIRTUAL_ENV CONDA_PREFIX
export POETRY_VIRTUALENVS_CREATE=true
export POETRY_VIRTUALENVS_IN_PROJECT=false
export POETRY_VIRTUALENVS_USE_POETRY_PYTHON=true
uvx --python 3.12 --from poetry==2.4.3 poetry env use 3.12
uvx --python 3.12 --from poetry==2.4.3 poetry install --with test --no-interaction
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m textui run examples/project/app.ui
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m examples.editor
```

Replace `examples/project/app.ui` with `examples/controls/app.ui`, `examples/data/app.ui` or `examples/components/app.ui` to try those projects. Run tests with `uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest -q`. To locate the managed environment, run `uvx --python 3.12 --from poetry==2.4.3 poetry env info --path`; do not assume `.venv/bin/textui` exists. An installed library also supports `python -m textui run /absolute/path/app.ui` using the Python interpreter where it was installed.

The [showcase](https://github.com/thunderballfists/TextUI/blob/main/examples/showcase/app.ui) combines every built-in widget family in one navigable project: components, layouts, controls, tables, trees, lists, logs, modals, actions, and timers. The project example demonstrates a linked Python controller, local TCSS, an included view, sidebar navigation, a resizable split, and a timer; see the [project runtime guide](https://github.com/thunderballfists/TextUI/blob/main/docs/project-runtime.md). The [component example](https://github.com/thunderballfists/TextUI/blob/main/examples/components/app.ui) demonstrates imported `.ui` components, literal properties, and slots. The [controls example](https://github.com/thunderballfists/TextUI/blob/main/examples/controls/app.ui) demonstrates form controls, tabs, radio choices, collapsible content, progress bars, and rules. The [data example](https://github.com/thunderballfists/TextUI/blob/main/examples/data/app.ui) demonstrates an API-backed runtime table beside seeded native tables and trees; see the [controls guide](https://github.com/thunderballfists/TextUI/blob/main/docs/controls.md). The separate editor is a small form demonstrating a Save action that updates a status label; it does not write a file. Press Ctrl+Q to quit. Its markup path is relative to the example module, independent of the working directory. Examples are included in the source distribution, not the installed library wheel.

For a linked-script project launched from Python, `ProjectApp(source, context=host_value)` makes `host_value` available as read-only `window.context` in the controller. Controllers may also define `on_resize(width, height)` to update width-sensitive content after the screen refreshes; see the [runtime lifecycle guide](https://github.com/thunderballfists/TextUI/blob/main/docs/project-runtime.md).

## Check a project

After checkout setup, validate a project without opening a terminal UI:

```sh
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m textui check examples/showcase/app.ui
```

`check` reads includes/components/styles, executes linked Python and `on_setup`, binds actions/commands, and constructs declared widgets including dormant modal contents. It checks document and inline TCSS with native theme variables. It does not mount widgets, run `on_ready`/`on_resize`, dispatch events, or start declared timers. `on_close` runs once after setup begins, including on validation failure. Linked scripts, setup/close hooks and factories remain trusted code and may have side effects; this is not a sandbox or a static-only check. Custom widget composition, mount hooks, default styles and layout still require a running-app test.

Both `check` and `run` report expected project errors on stderr with source context. Add `--debug` before or after the command for their tracebacks. Status codes are 0 for success, 1 for a project error, 2 for invalid CLI usage, 3 for an unexpected failure (with traceback), and 130 for interruption. `run` also preserves an explicit application exit code. See the [validation guide](https://github.com/thunderballfists/TextUI/blob/main/docs/project-runtime.md#project-validation) for the full boundary.

## Python integration

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

The project runtime accepts only linked scripts declared at the entry root; the standalone `DocumentLoader` does not load scripts. Text in leaf widgets is literal, with whitespace collapsed; nested markup in leaves and mixed text/widget content are unsupported.

### Syntax

TextUI uses strict XML parsing for its own markup vocabulary. Documents must be well-formed UTF-8 with one attribute-free `<ui>` root, quoted attribute values, and closed or self-closing tags. Names are lowercase kebab-case; booleans are exactly `"true"` or `"false"`. Comments and CDATA are allowed. Only the five predefined named entities (`&amp;`, `&lt;`, `&gt;`, `&quot;`, `&apos;`) are supported, alongside numeric character references. DTDs, namespaces, processing instructions, unknown tags/attributes/events, and duplicate IDs are rejected.

### Not a subset of HTML

The HTML-like feel does not imply browser compatibility. Tags such as `vertical`, `split`, `switch`, and `data-table` are TextUI controls; shared names such as `input` and `select` have TextUI attributes and content rules. Self-closing `<switch />` and `<data-table />` work here, while HTML parsers ignore `/>` on non-void elements. Bare boolean attributes and HTML named entities such as `&nbsp;` are invalid. `on-pressed="save"` names a Python action, not JavaScript.

| Tag | Content | Attributes beyond common attributes | Events |
| --- | --- | --- | --- |
| `vertical`, `horizontal` | Widgets | None | None |
| `label` | Text | None | None |
| `button` | Text | `variant`: default, primary, success, warning, error | `pressed` |
| `input` | None | `value`, `placeholder`, `password`, positive `max-length` | `changed`, `submitted` |
| `checkbox` | Text | Boolean `value` | `changed` |
| `split` | Exactly two `pane` children | `direction`: horizontal or vertical | `resized`, `toggled` |
| `pane` | Widgets | Positive `min-size`, optional `size` | None |
| `nav` | `nav-item` children | None | `selected` |
| `nav-item` | Text | Required `target` ID | None |
| `content-switcher` | Widgets with IDs | Optional `initial` child ID | None |
| `select` | `option` children | `value`, `prompt`, boolean `allow-blank` | `changed` |
| `option` | Text | Required `value` | None |
| `switch` | None | Boolean `value` | `changed` |
| `text-area` | Verbatim text | `language`, `soft-wrap`, `read-only`, `show-line-numbers`, `tab-behavior`, `placeholder` | `changed` |
| `tabbed-content` | `tab-pane` children | Optional `initial` pane ID | `tab-activated` |
| `tab-pane` | Widgets | Required `id` and `title` | None |
| `radio-set` | `radio-button` children | None | `changed` |
| `radio-button` | Text | Boolean `value` | `changed` |
| `collapsible` | Widgets | `title`, boolean `collapsed` | `collapsed`, `expanded` |
| `progress-bar` | None | Positive `total`, nonnegative `progress`, boolean `show-bar`, `show-percentage`, `show-eta` | None |
| `range` | None | Integer `min`, `max`, positive `step`, optional aligned `value`, boolean `show-value` | `changed` |
| `rule` | None | `orientation`, `line-style` | None |
| `header`, `status-bar` | Optional `left`, `center`, and `right` slots | None | None |
| `log` | None | Optional `max-lines`, boolean `auto-scroll`, `wrap`, and `highlight` | `on-selection-ended` |
| `list` | None | Required `item-label` with direct mapping-key fields | `selected` |
| `modal` | Widgets; document root only | Required `id`, boolean `dismissable` | None |
| `data-table` | `column` children, then `row` children | `cursor-type`: row, cell, column, none; optional `row-key`; boolean `striped`, `column-borders`, `resizable` | `row-selected`, `cell-selected` |
| `column`, `row`, `cell` | Column/cell text; rows contain cells | Columns: required `key`, optional `label`, `align`, positive `width`; rows: required `key` | None |
| `tree` | Nested `tree-node` children | Required `label`, boolean `show-root` | `node-selected` |
| `tree-node` | Nested `tree-node` children | Required `key` and `label`, boolean `expanded` | None |

Mounted widgets accept `id`, whitespace-separated `class`, `disabled`, and literal `style`; `option`, `column`, `row`, `cell`, and `tree-node` are data-only children and do not accept these attributes. Boolean values must be `true` or `false`. An event attribute such as `on-pressed="save_document"` names an exact exposed action key; it cannot contain expressions, arguments, or dotted paths. Callbacks take one `ActionContext` containing `event`, `widget`, `app`, and the bound `document`. Both synchronous and asynchronous callbacks work. Initialization events follow Textual's normal behavior. Actions do not automatically stop bubbling or prevent default behavior; errors propagate as `ActionExecutionError` with the original cause.

`split` uses a draggable divider that accepts arrow keys when focused. Set `pane.display = False` to hide a pane; showing it restores its stored size. A `nav-item` target must name a direct child of a `content-switcher`. The `selected` event carries `context.event.target`, which an action can assign to the switcher's `current` property. The [project example](https://github.com/thunderballfists/TextUI/blob/main/examples/project/app.ui) shows these controls together.

## Reusable project components

Project entry files may import a local component directly below `<ui>`, then use its lowercase kebab-case alias as a widget:

```xml
<component src="components/agent-card.ui" as="agent-card" />
<agent-card id="alpha" name="Alpha">
  <slot name="actions"><button on-pressed="open_alpha">Open</button></slot>
</agent-card>
```

A component file has a `<component>` root, optional string `<props>`, and exactly one widget root. Literal `{property}` placeholders work in text and attribute values. Named `<slot>` declarations accept caller content and otherwise retain their fallback widgets. The instance `id`, class, style, disabled state, and events apply to the rendered root; template IDs are private and receive unique instance prefixes. Components may import other components, but cannot contain scripts or styles. See the [project runtime guide](https://github.com/thunderballfists/TextUI/blob/main/docs/project-runtime.md) and runnable [component example](https://github.com/thunderballfists/TextUI/blob/main/examples/components/app.ui).

## Integrate with a normal App

Bind after `App.__init__` and before the App runs. Compose the binding through the normal Textual hook, then explicitly forward native messages. [The runnable editor](https://github.com/thunderballfists/TextUI/blob/main/examples/editor.py) implements this complete pattern:

```python
from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Button, Checkbox, Input, Select, Switch, TabbedContent, TextArea
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
    @on(Select.Changed)
    @on(Switch.Changed)
    @on(TextArea.Changed)
    @on(TabbedContent.TabActivated)
    async def forward_document_message(self, event) -> None:
        await self.document.dispatch(event)


Host(DocumentLoader().from_string("<ui><label>Hello</label></ui>")).run()
```

`TextUI` supplies these built-in handlers for convenience. Add decorators for any other component messages used by your document. `get_by_id` returns only widgets with declared document IDs and requires them to be mounted. Use native `app.query()` / `app.query_one()` for general selectors. A `Document` can be reused in independent Apps; each binding constructs fresh widgets. There is one binding per App and a single composition attempt per binding. Recomposition, remounting, document replacement, and transparent attachment to a running App are unsupported.

Normal hosts must call `self.document.close()` when shutdown begins and on unmount to cancel owned actions and commands; the convenience Apps do this automatically. Closing is idempotent and ignores later queued document events. See the [runtime lifecycle guide](https://github.com/thunderballfists/TextUI/blob/main/docs/project-runtime.md) for shared loading targets, supersession, and cooperative cancellation.

## Add components and events

`ComponentRegistry()` starts empty. To extend the built-ins, use `default_component_registry` from `textui.widgets.builtin_widgets`, then register additional immutable `ComponentSpec` definitions. Construct `DocumentLoader(registry)` after registration; the loader snapshots the registry.

Inspect attribute types, defaults, events and ordered content rules with `registry.describe()` or `spec.describe()`. Frozen types and content constraints support explicit custom metadata while preserving existing callable converters. Inspection does not invoke converters or factories. See the [registry metadata guide](https://github.com/thunderballfists/TextUI/blob/main/docs/registry-metadata.md); generated schemas and static checking are planned separately.

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

Declare custom events with `events={"updated": EventSpec(CustomMessage, lambda event: event.widget)}` on the component spec, using the message's actual source-widget property. The host must also implement `@on(CustomMessage)` and `await self.document.dispatch(event)`. Subclassing `TextUI` is sufficient. Dispatch matches the **exact registered message type** and originating widget identity; no handlers are discovered automatically. See the [tested custom component and message example](https://github.com/thunderballfists/TextUI/blob/main/tests/test_extensions.py).

## Styles and trust

Embedded `<style>` blocks use native TCSS and are App-wide. The project runtime also accepts `<style src="file.tcss"/>`, `<style preset="compact"/>`, and `<style preset="borders"/>` at the entry root. A linked controller can call `window.document.toggle_style_preset("compact")` or `window.document.toggle_style_preset("borders")` to switch a declared preset at runtime. Styles follow host `CSS` / `CSS_PATH` author rules and retain document block order at equal specificity and importance. Native specificity, `!important`, widget defaults, and inline priority still apply. Inline declarations use native `set_styles`; they may contain literal values but not variable references. Put variables in a `<style>` block or host TCSS. Theme variables are available, while variables declared within one embedded block are local to that source. Standalone hosts may use `CSS_PATH` for external styles. `header` and `status-bar` IDs may use `background: linear-gradient(angle, color, color, ...)` with a degree angle and literal colors; `0deg` is horizontal and `90deg` is vertical. TextUI renders that gradient beneath their controls.

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

TextUI is released under the [MIT License](https://github.com/thunderballfists/TextUI/blob/main/LICENSE).
