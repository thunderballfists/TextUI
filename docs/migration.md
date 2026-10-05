# Migrating to TextUI

## Distribution name in 0.7

The distribution is now `textui-markup` (version 0.7.0); `import textui`, the `textui` command, `.ui` files, and the MIT license are unchanged. Replace Git-based requirements named `textui` with `textui-markup==0.7.0`. For development from Git, `textui-markup @ git+https://github.com/thunderballfists/TextUI.git@COMMIT` can pin a commit containing the rename.

Use a fresh virtual environment when migrating an existing installation. Alternatively, uninstall the old distribution **before** installing the new one: `python -m pip uninstall textui`, then `python -m pip install textui-markup==0.7.0`. Installing both and subsequently uninstalling either can remove shared import files. The unrelated PyPI project named `textui` is not this framework.

The product is described as HTML-like markup; its parsing rules are unchanged. See the README [Syntax](../README.md#syntax) and [HTML differences](../README.md#not-a-subset-of-html).

## Unreleased component guidance

For runtime lists inside reusable components, pass record formats through a component property, such as `row-format="{name}"` at the call site and `item-label="{row-format}"` in the template. Direct braces in templates refer to component properties; doubled braces do not escape component substitution. See the [component formatting example](project-runtime.md#reusable-components).

## Interface reboot in 0.2

Version 0.2 replaces the experimental 0.1 interface. Documents and APIs intentionally break compatibility. The [README](../README.md), [changelog](../CHANGELOG.md), [examples guide](../examples/README.md), and [editor example](../examples/editor.py) show the current usage and release scope.

| Earlier interface | 0.2 replacement |
| --- | --- |
| `TextUI(markup_string)` or a guessed file path | `TextUI(DocumentLoader().from_string(markup))` or `.from_file(path)` |
| Arbitrary outer wrapper such as `<container>` | One attribute-free `<ui>` root, containing widgets and direct `<style>` blocks |
| `<script>`, `document` / `window` script globals | Trusted Python callbacks exposed through `actions={"name": callback}` |
| `add_event_listener(...)` | Declared attributes such as `on-pressed="save_document"` and explicit message forwarding in a normal host App |
| Broad HTML aliases, underscore tags, image widgets | The six tags `vertical`, `horizontal`, `label`, `button`, `input`, `checkbox`; register deliberate adapters for anything else |
| Nested markup inside labels or buttons | Literal leaf text; use container widgets for composition |
| Browser-style `get_element_by_id`, `get_widget_by_id`, class/tag queries | Mounted `bound_document.get_by_id("name")`; native App queries for selectors |
| Custom CSS filtering and dimension rewriting | Native TCSS validation and `Widget.set_styles` for literal inline declarations |
| Hand-built append-only transcript widgets | `<log>` with controller `append()`, `append_inline()`, and `commit_line()` methods |

## Load explicitly

```python
from textui import DocumentLoader, TextUI

definition = DocumentLoader().from_file("examples/sample_markup.xml")
app = TextUI(definition)
app.run()
```

Files are UTF-8 and retain a resolved source path. `from_string` never treats its input as a filename. Loader failures now raise contextual public errors instead of repairing input or silently ignoring invalid content.

## Reuse project markup

The project runtime can import a local `.ui` component directly below its entry root: `<component src="components/card.ui" as="agent-card"/>`. The component definition has a `<component>` root, optional literal string `<prop>` declarations, and one widget root. Use `{property}` in template text or attribute values, and use named `<slot>` placeholders for caller-provided widgets with fallback content. Public instance attributes apply to that root, while template IDs are isolated per instance. Scripts and styles remain entry-only. See the [project runtime guide](project-runtime.md#reusable-components).

Use lowercase kebab-case names (`max-length`, not `max_length`). Booleans are exactly `true` and `false`; numbers and enums are validated. `class="primary compact"` means two independently validated class tokens, and duplicates are removed. IDs must be unique and valid; anonymous widgets do not receive generated IDs. Set `autofocus="true"` on a focusable control or component instance to receive focus after it mounts or is revealed by a `display` change; inside a tab pane, it waits for that pane to activate. Disabled or hidden controls do not take focus. Whitespace in leaf text collapses and brackets remain literal rather than becoming Rich markup.

## Move behavior into Python

Callbacks receive one `ActionContext`. Register an exact action key and reference it in markup. For example, `on-pressed="save_document"` calls the callback registered under `save_document`. Strings containing expressions, arguments, imports, and dotted names are rejected. Both sync and async callbacks work; callback exceptions become `ActionExecutionError` and propagate with their cause intact.

The convenience `TextUI` App forwards Button.Pressed, Input.Changed, Input.Submitted, and Checkbox.Changed. A normal App must compose the binding and forward these messages itself; the [editor](../examples/editor.py) demonstrates this. Custom registered events always require an explicit host `@on(CustomMessage)` forwarder. Message matching uses the exact registered type, not subclass matching. Native bubbling and initialization events remain in effect.

Bind once after `App.__init__`, before startup. Lookup is available only after mounting and stops working after removal. Bindings have one composition attempt, including failure; create a fresh App and binding to retry. A definition may be shared across independent Apps, but widgets and action mappings belong to their own binding. Recomposition, remounting, and replacement inside a running App are outside the initial lifecycle contract.

## Keep native styling semantics

Use `<style>` only directly below `<ui>`. Styles are App-wide, and document rules follow host author styles, with later document blocks following earlier blocks at equal specificity and importance. Textual controls specificity, `!important`, default styles, and inline priority. Invalid declarations now raise `DocumentStyleError`; they are not stripped.

Inline `style` accepts literal TCSS declarations only. Move variable-dependent declarations into embedded or host TCSS. Theme variables work in embedded blocks; variables declared in a block are native source-local and cannot be referenced by another block. Set external `CSS_PATH` on the host App. Error locations report source/element lines and native CSS details; XML entity or CDATA decoding can prevent exact source-column mapping.

## Dependencies and trust

The core targets Python `>=3.11,<4`, Textual `>=8.2.8,<9`, and lxml `>=6.1.3,<7`. Pillow and textual-imageview are no longer core dependencies. The previous `<img>` adapter and image assets are removed; an optional image extension is a separate future capability, not a current extra.

Developer-authored markup and trusted Python registrations are required. Strict XML parsing does not establish an untrusted-document security guarantee. The standalone loader does not execute Python; linked scripts are supported by the trusted project runtime.
