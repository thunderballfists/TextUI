# TextUI minimal core design

Date: 2026-09-17

Status: proposed specification for review. The owner approved the audit's five architectural decisions; the detailed contracts below require review before implementation planning.

Basis: [repository audit](../../audits/2026-09-17-repository-audit.md), including successful tests on Textual 3.3.0, 3.7.1, and 8.2.8 and the defects reproduced on both comparison releases.

## 1. Scope and approved decisions

TextUI is a declarative authoring layer: XML supplies structure, TCSS supplies appearance, Python supplies behavior, and Textual owns execution and rendering.

The first release of the redesigned core permits breaking pre-1.0 APIs and documents. It provides an independent document loader, optional `TextUI(App)` convenience, strict `<ui>` XML with kebab-case names, an explicit typed component registry, registered actions, and six built-in widgets. Retain lxml initially; imaging becomes optional. Support one document binding per App, literal inline styles, and variable-dependent styles in TCSS stylesheets.

Exclude embedded scripts, expressions, templates, automatic data binding, hot reload, transparent wrapping of running apps, multiple document bindings within one App, browser HTML semantics, and a new renderer. Documents and component/action registrations are developer-controlled. This release makes no untrusted-document security claim.

## 2. Public objects and data flow

The names below define the proposed API, not implemented code.

| Object | Responsibility |
| --- | --- |
| `ComponentRegistry` | Holds explicit `ComponentSpec` records; rejects duplicate tags. |
| `DocumentLoader` | Parses file/string input and validates grammar, attributes, IDs, component content, and declared event names. |
| `Document` | Immutable validated definition: component nodes, source locations, style blocks, action references, and a registry snapshot. No widgets, App, or bound callbacks. |
| `BoundDocument` | One App's instance: exposed callbacks, native widgets, ID index, message bindings, and styling/lifecycle state. |
| `ActionContext` | Callback argument containing `event`, `widget`, `app`, and the bound `document`. |
| `TextUI` | Thin App convenience that composes a bound document and forwards supported native control messages. |

```python
loader = DocumentLoader()  # six built-in component definitions
document = loader.from_file("form.xml")
# Alternatively: loader.from_string(markup, source_name="<string>")
app = TextUI(document, actions={"save_document": save_document})
app.run()
```

`from_file(path: str | Path) -> Document` reads UTF-8 and retains the resolved source path. `from_string(markup: str, *, source_name: str = "<string>") -> Document` never guesses that its argument is a filename. Missing/unreadable files produce a source-aware loading error with the original exception attached.

`Document.bind(app: App, *, actions: Mapping[str, ActionCallback]) -> BoundDocument` validates required action names and callability before any widgets or stylesheet mutations. Call it after `App.__init__`, before running the App. Copy the registry/action mappings so later registration changes cannot silently alter an existing document. Reusing a `Document` in different Apps creates independent bindings and widgets. A second binding to the same App is rejected.

The phases are: parse → validate/convert → bind actions → prepare TCSS and construct widgets during composition → Textual mounts → handle messages. Parse/validation must not instantiate components or execute actions. Constructors remain trusted Python and may have side effects; validation is not a transactional sandbox.

## 3. Document grammar

Require exactly one `<ui>` root. It is a document wrapper, never a widget, and accepts no attributes. Its children are registered components or `<style>` blocks. Permit multiple top-level components and an empty document.

Tag and attribute names are lowercase kebab-case; underscores and namespaces are rejected. IDs and class tokens use Textual's identifier rules, independently of tag naming. XML comments are ignored. Reject processing instructions, DTDs, entity references, unknown elements/attributes, and `<script>`. XML declarations specifying supported UTF-8 input are permitted. Syntax repair is never performed.

`<style>` is allowed only directly inside `<ui>`, has no attributes or element children, and may use CDATA. Retain CSS text verbatim; do not collapse its whitespace. Style blocks are applied in document order.

For components, text policy is explicit: `none` permits only formatting whitespace; `text` accepts text but no markup children and collapses whitespace runs to a single space with outer whitespace trimmed. Child policy is independently `none` or `widgets`; do not permit mixed text/widget content in the first core. Non-whitespace tail text is rejected. Labels are literal text, not implicitly interpreted as Textual/Rich markup.

IDs are unique across the entire document. Do not generate IDs for anonymous widgets. Split `class` on whitespace, validate each token, and deduplicate tokens without changing their meaning. Reject empty explicit IDs and invalid class tokens with element context.

```xml
<ui>
  <style>
    #form { padding: 1 2; }
    .primary { width: 20; }
  </style>
  <vertical id="form">
    <label>Name</label>
    <input id="name" placeholder="Document name" />
    <checkbox id="notify" value="false">Notify when saved</checkbox>
    <horizontal>
      <button class="primary" on-pressed="save_document">Save</button>
    </horizontal>
  </vertical>
</ui>
```

## 4. Typed registry and construction

Use small immutable dataclasses and explicit converter functions. Do not derive the markup schema from constructor introspection or add a schema-framework dependency.

`ComponentSpec` contains `tag`, attribute specifications, text policy, child policy, event specifications, and a trusted factory. `AttributeSpec` contains a converter, required/default information, and constraints. `EventSpec` contains the native `message_type` and a `source_widget(message)` function. Registry errors, including duplicate tags and reserved directive names, are configuration errors.

The factory has the conceptual signature `factory(context: BuildContext) -> Widget`. `BuildContext` contains read-only converted attributes, normalized text, constructed child widgets, and the source location. It does not expose mutable XML nodes. Factories explicitly map markup attributes to constructor arguments; custom factories use this same interface. A factory must return a fresh, unmounted Widget. Validate return type and parent/mount state, and reject reuse of returned instances within the constructed document. Internal descendants created later by a trusted custom component remain subject to Textual's lifecycle rules.

Common core attributes are `id`, `class`, `style`, and boolean `disabled`. The common layer applies IDs/classes/disabled and literal inline styling to the returned widget. Factories handle component-specific attributes and receive/attach permitted children once. Textual owns layout and rendering; special constructors require deliberate adapters.

Boolean conversion accepts only `true` and `false`. Integer conversion requires a base-10 integer and then applies its range constraint. Enum conversion requires an exact listed spelling. Report both the attribute value and expected domain when conversion fails; do not use Python truthiness or silent fallback. Optional attributes without a specified default are omitted from factory arguments.

| Tag | Content | Component attributes beyond common attributes | Events |
| --- | --- | --- | --- |
| `vertical` | Widget children | None | None |
| `horizontal` | Widget children | None | None |
| `label` | Text | None | None |
| `button` | Text | `variant`: default/primary/success/warning/error; default `default` | `pressed` |
| `input` | None | `value`, `placeholder`: strings defaulting to empty; `password`: boolean default false; optional `max-length`: positive integer | `changed`, `submitted` |
| `checkbox` | Text | `value`: boolean default false | `changed` |

Container adapters pass their children through native construction. Leaf adapters must preserve literal label content using the appropriate Textual content type. A test using brackets in label text proves that escaping is correct.

## 5. Native App integration and lifecycle

`BoundDocument.compose() -> Iterable[Widget]` prepares the complete document before yielding its top-level widgets. This runs inside the host's ordinary composition phase. Preparation validates styles against the App's available stylesheet context, constructs a fresh native tree, builds indexes, and installs document TCSS once. If validation/construction fails, do not yield any document widgets or leave partially installed document styles.

An existing App opts in explicitly:

```python
class Editor(App):
    def __init__(self, document):
        super().__init__()
        self.ui = document.bind(self, actions={"save_document": self.save_document})

    def compose(self):
        yield from self.ui.compose()

    @on(Button.Pressed)
    @on(Input.Changed)
    @on(Input.Submitted)
    @on(Checkbox.Changed)
    async def forward_document_message(self, event):
        await self.ui.dispatch(event)

    async def save_document(self, context):
        name = context.document.get_by_id("name").value
        self.notify(f"Saving {name}")
```

This is an illustrative API example; imports come from Textual and the new package exports. `TextUI` provides the same four message handlers and composition hook. Neither path monkey-patches the host nor overrides private message dispatch.

Bindings are single-use: calling `compose()` again after successful preparation raises `DocumentStateError`. Recomposition, unmount/remount of the same binding, and replacing documents in a running App are outside the initial lifecycle contract. A fresh binding in a fresh App is the supported reuse path. The instance lifetime equals the App lifetime, including installed TCSS; no standalone stylesheet removal protocol is required for this phase.

`get_by_id(id: str) -> Widget` looks up only the document's declared IDs and requires the widget to be mounted. It raises `DocumentStateError` before mounting/after removal and `ElementNotFoundError` for an absent ID. Arbitrary Textual queries remain available on the host; omit the browser-style tag/listener facade. Host-authored widgets outside this document still obey Textual's own ID and layout rules.

## 6. Registered actions and custom events

An attribute `on-<event>="action_name"` references an event declared by that component and an exact key in the host's actions mapping. Action names are nonempty Python-style identifiers, used only as mapping keys. Reject expressions, arguments, dotted paths, imports, and unknown names. Multiple handlers for one attribute are not supported.

`ActionCallback` receives exactly one `ActionContext` and returns `None` or an awaitable resolving to `None`. The dispatcher calls the callback once, then awaits its result when necessary; it does not start background tasks automatically. Long-running work uses the host's normal Textual worker APIs.

`BoundDocument.dispatch(message: Message) -> bool` uses the registered message type and source-widget extractor to find a binding by widget identity, not by a global CSS selector. Return false when the message has no document binding; otherwise await the action and return true. The first core uses exact declared message types to avoid ambiguous inheritance matching. Do not stop bubbling or prevent native behavior automatically. The callback may explicitly do so through its event. Events emitted during initialization are not suppressed; they follow normal Textual lifecycle semantics.

Action exceptions become `ActionExecutionError` with action name, binding location, and the original exception as cause, and propagate through the normal host error path. Never silently log and continue as the existing script implementation does.

Custom components register typed attributes, content policy, factory, and optional `EventSpec` entries. The host forwards each custom native message with its own `@on(CustomMessage)` method calling `dispatch`; custom-message forwarding is an explicit integration responsibility. Subclassing the convenience App is sufficient for this. The first proof must register a status component and forward a custom message without changing core. Document this obligation beside event registration, rather than implying automatic discovery.

## 7. TCSS ownership and errors

Delegate TCSS syntax, declarations, cascade, and validation to Textual. Delete the regex-based filter from the new core; never sanitize by silently removing declarations.

Embedded blocks are whole TCSS sources, with stable source identifiers derived from the document source and block index. Stage additions and parse them against a copy of the host stylesheet before installing them. During normal App startup, host `CSS`/`CSS_PATH` sources are available before document composition; preserve that ordering in an integration test. Keep all access to Textual stylesheet internals in one adapter so upgrades have a small review surface.

Document styles are App-wide, not an isolated CSS scope. Preserve Textual specificity and `!important`. At equal specificity and importance, document rules follow host author rules, and later document blocks follow earlier ones. Widget default styles retain Textual's normal lower priority. Add computed-style tests for these cases before claiming support.

For `style`, apply literal declarations through `Widget.set_styles()`. Inline styles retain native Textual priority; do not synthesize selector rules. Reject variable references with a specific diagnostic directing the author to a `<style>` block or host TCSS. Do not introduce a second declaration grammar to implement this check; use Textual parsing/token information in the adapter.

Style errors include document source, the containing block or element line, and Textual's original error details. For embedded blocks, preserve relative CSS line/column information and map lines to the original document when available. XML entity/CDATA decoding can prevent an exact source-column mapping; never report invented attribute-level columns.

External TCSS remains a host concern through `CSS_PATH`; the initial XML grammar has no stylesheet import directive. Styles cannot trigger Python execution in this design, but that fact does not establish a broader untrusted-input policy.

## 8. Parsing, diagnostics, and dependencies

Use strict `lxml.etree` parsing: recovery off, network access off, DTD loading off, entity resolution off, and huge-tree mode off. Reject DTD/entity content and namespaces explicitly, ignore ordinary comments, and never run XInclude. Capture each node's source line before lowering it to immutable records. Syntax errors retain parser line/column details; semantic errors identify the element and attribute but promise only reliable node-line precision.

Public errors derive from `TextUIError`: `DocumentLoadError`, `DocumentSyntaxError`, `DocumentValidationError`, `DocumentStyleError`, `ComponentBuildError`, `DocumentStateError`, `ElementNotFoundError`, and `ActionExecutionError`. Each appropriate error carries a source location and structured context alongside a readable message. Registry configuration errors use a separate `RegistryError` under the same base. Fail deterministically at the first error in document order; aggregating diagnostics is deferred.

Example: `form.xml:12 <checkbox> attribute 'value': expected true or false; got 'maybe'`.

Initial implementation target: Python `>=3.11,<4`, Textual `>=8.2.8,<9`, and lxml `>=6.1.3,<7`. The audit's saved PyPI metadata identifies 6.1.3 as the current lxml release; this is a proposed upgrade from the tested 4.9.x parser, requiring compatibility checks. Use pytest and pytest-asyncio for tests. Run the release test matrix on Python 3.11, 3.12, and 3.14, recording exact resolved versions. The existing audit validates current Textual only on Python 3.12; do not present the broader matrix as already verified. Confirm installation and strict-parser behavior across that matrix before locking dependencies.

Core installation must not install or import Pillow/textual-imageview. Images remain an optional follow-up extra and component registration, with dedicated file-path/load/resize/dimension tests; they are not a seventh core widget. Developer-authored documents and trusted callbacks/factories are the only supported trust model. A later untrusted mode needs separate capability and resource-limit design.

## 9. Package boundaries and migration

Organize by responsibility: `loader.py` parses/validates documents; `registry.py` defines component metadata and converters; `document.py` holds definitions and bound instances; `actions.py` handles contexts/dispatch; `styling.py` isolates Textual style integration; `errors.py` holds diagnostics; `widgets/` contains the six native adapters; `textui.py` contains the convenience App. Adjust the split only when implementation shows a concrete dependency issue; avoid a generic framework of layers.

Export the loader, registry/spec types, Document/BoundDocument, ActionContext, TextUI, and public errors from the package root. The old `TextUI(markup_string)` constructor, arbitrary root wrapper, scripts, HTML aliases, broad built-in registry, DOM aliases, and custom CSS filtering are intentionally not compatibility requirements. Provide a short migration guide and tested examples. Retain the original audit as characterization evidence, not the old behavior as the new contract.

## 10. Acceptance gates

1. **Validation:** string/file parity, explicit missing-file errors, strict root/namespace/comment rules, unknown tags/attributes/events/actions, duplicate IDs, enum/bool/integer conversion, content policies, and source context. Parsing creates no widgets and invokes no callbacks.
2. **Rendering:** each of six widgets, nested parentage, multiple roots, plain bracketed labels, multiple classes, fresh instances across Apps, rejected repeated composition, and correct mounted lookup behavior.
3. **Styling:** embedded block order, host/document/default/inline cascade, literal declarations, rejected inline variables, theme variables in stylesheets, invalid TCSS diagnostics, and failure without partial stylesheet installation. Assert computed styles, not merely source strings.
4. **Actions:** Pilot click/change/submit events, synchronous and asynchronous callbacks, source identity, initialization-event behavior, missing bindings, propagated exceptions, and no unintended double dispatch from the supplied convenience host.
5. **Extensions:** application-defined typed component, fresh-instance enforcement, custom message forwarding, and constructor errors with source context, without edits to core.
6. **Packaging/docs:** supported Python matrix, bounded Textual dependency, core without imaging packages, runnable README examples, and explicit migration/trust limitations. Existing local files are not silently incorporated or discarded during implementation.

The audit's scripts/tests that assert removed behavior must be replaced with rejection or new-contract tests when their feature changes. Every behavioral change requires a meaningful failing test before implementation. No implementation is authorized merely by completing this document.

## Review checkpoint

Approve this detailed specification before creating the task-by-task implementation plan. In particular, the API and lifecycle choices to review are explicit host message forwarding, one binding per App, single-use composition, App-wide embedded TCSS, and custom events forwarded by the host.
