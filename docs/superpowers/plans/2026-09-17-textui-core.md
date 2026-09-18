# TextUI Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Deliver the approved declarative Textual core with strict validation, native styling, registered actions, a documented extension API, and a verified Python matrix.

**Architecture:** A pure loader lowers strict XML to an immutable Document using a registry snapshot. A BoundDocument prepares a native widget tree and stylesheet transaction for one App; TextUI is an optional convenience App using ordinary native message handlers.

**Tech Stack:** Python, Textual, lxml, pytest, pytest-asyncio, Poetry packaging.

**Spec:** `docs/superpowers/specs/2026-09-17-textui-core-design.md` (approved by the owner on 2026-09-17).

## Global Constraints

- Python `>=3.11,<4`, Textual `>=8.2.8,<9`, and lxml `>=6.1.3,<7`.
- Release tests run on Python 3.11, 3.12, and 3.14; exact resolved versions are recorded.
- Strict `<ui>` XML, lowercase kebab-case tags and attributes, literal leaf text, six built-ins: vertical, horizontal, label, button, input, checkbox.
- One document binding per App; bindings have single-use composition; document definitions can be reused across independent Apps.
- Native App-wide TCSS, host-before-document author order, document block order, native inline priority, and no variables in inline declarations.
- Exposed action names only; exact registered native message types; explicit host forwarding for custom messages. No exec, dynamic import strings, private dispatch overrides, automatic handler discovery, or expression language.
- Developer-authored documents and trusted registrations; no untrusted-input security claim.
- Core imports/installation exclude Pillow and textual-imageview. Optional imaging is a follow-up capability, not part of the six-widget release.
- Preserve all existing local changes in the original checkout. Work only in `.worktrees/textui-core` on `codex/textui-core`.
- Follow TDD: record the initial expected failure before implementation and final passing command in each task report. Do not create tests that merely inspect source text.
- Implementers do not delegate. The controller supplies task and final review. Stage only owned files; each task commits its changes.

## File and interface map

- `errors.py`: immutable `SourceLocation(source: str, line: int | None, column: int | None = None, tag: str | None = None)` and public exception hierarchy. Exceptions accept message plus location/attribute/value context, preserving `__cause__`.
- `registry.py`: immutable AttributeSpec, EventSpec, ComponentSpec, BuildContext; ComponentRegistry; boolean/integer/enum converters. Factories consume BuildContext and return Widget.
- `nodes.py`: immutable `ElementNode(spec, attributes, common, text, children, events, location)`, `StyleBlock(content, location, index)`; mappings frozen/copied. `common` carries id/classes/style/disabled; `events` maps event names to action names.
- `loader.py`: DocumentLoader(registry=None).from_string(markup, source_name="<string>") and .from_file(path).
- `document.py`: Document(nodes, styles, source_name) data definition (Task 1); .bind and BoundDocument (Task 2). Nodes retain immutable ComponentSpec references from a registry snapshot.
- `widgets/builtin_widgets.py`: registry builder and six explicit factories. Old broad widget factory and HTML definitions are replaced, not loaded by the new API.
- `actions.py`: ActionContext and callback typing; runtime dispatcher may live with BoundDocument to avoid cyclic state.
- `styling.py`: native stylesheet preparation/commit and inline validation, the only module accessing stylesheet internals.
- `textui.py`: TextUI(Document, actions=None, **app_options), native compose and four @on handlers.
- `__init__.py`: public exports; no imaging imports.
- Tests grouped by loader/registry, runtime/styles/actions/extensions; README, migration document, runnable example, dependency lock, CI.

Concrete dataclass parameter names are agreed across tasks: `AttributeSpec(converter=str, required=False, default=UNSET)`, `EventSpec(message_type, source_widget)`, `ComponentSpec(tag, factory, attributes={}, text_policy="none", child_policy="none", events={})`, and `BuildContext(attributes, text, children, location)`. Use immutable copied mappings. Constraint converters raise ValueError describing the domain; loader wraps them with document context. If a concrete implementation exposes an unavoidable mismatch, resolve it against the spec and record it, rather than silently inventing a second interface.

## Task 1: Strict document loader, registry, and component definitions

**Files:** Create `textui/errors.py`, `registry.py`, `nodes.py`, `loader.py`, `tests/test_loader.py`, `tests/test_registry.py`; replace `document.py` with the immutable definition and `widgets/builtin_widgets.py` with the six adapters; update `__init__.py`. Remove obsolete script/CSS/style tests and the legacy modules they exclusively exercise once no new import depends on them. The runtime/App replacement is Task 2, so do not export the old App from the new package root in this task.

**Consumes:** Approved spec sections 2–4 and 8, native Textual 8.2.8 constructors. Development interpreter `.venv/bin/python` already exists with Textual/lxml/test dependencies.

**Produces:** Public DocumentLoader, ComponentRegistry, ComponentSpec, AttributeSpec, EventSpec, BuildContext, SourceLocation, errors, and immutable Document data. The exact node fields in the interface map are consumed by Task 2.

- [ ] Write behavior tests before implementation. Start with a public-API availability assertion, then assert real typed outcomes and errors. Example:

```python
def test_false_and_classes_are_normalized_without_constructing_widgets():
    import textui
    assert hasattr(textui, "DocumentLoader"), "The new loader API is missing"
    doc = textui.DocumentLoader().from_string(
        '<ui><checkbox id="notify" class="one two one" value="false">Notify</checkbox></ui>'
    )
    node = doc.nodes[0]
    assert node.attributes["value"] is False
    assert node.common["classes"] == ("one", "two")
    assert node.text == "Notify"
```

Add table cases for unknown tag/attribute/event, root attributes, underscore/namespaced tags/attributes, duplicate IDs in different branches, empty ID, invalid bool/int/enum, missing required custom attributes, scripts/DTD/entities/PI, malformed XML, comments, permitted UTF-8 XML declaration, style CDATA preservation and restrictions, child/text/tail rules, file/string parity and missing file context. Use custom factory counters to assert no construction during load. Exercise registry duplicates/reserved names, immutable snapshots, and default-value isolation.

- [ ] Run `.venv/bin/python -m pytest tests/test_loader.py tests/test_registry.py -q`, capture expected RED before implementing.
- [ ] Implement the dataclasses, converters, and strict parser. Use native Textual identifier validation. Decode files explicitly as UTF-8; parser receives correctly encoded bytes so permitted XML declarations work. Scan prolog/tree for PI/DTD/entity nodes without enabling DTD resolution. Ignore comments without losing meaningful text around them. Lower to immutable nodes; convert common attributes before construction; validate one event name per supported EventSpec. Use exact booleans and positive max-length. Factories map normalized values explicitly:

```python
def build_vertical(context):
    return Vertical(*context.children)

def build_input(context):
    options = dict(context.attributes)
    if "max-length" in options:
        options["max_length"] = options.pop("max-length")
    return Input(**options)
```

Use native literal Content/Text types for label/button/checkbox rather than interpreting bracketed text. Keep factory construction separate from parser validation. Implement all public error types now for Task 2. Document has a local-import bind method only when Task 2 supplies runtime; no placeholder public method that silently succeeds.

- [ ] Run focused tests to GREEN, then the task's complete test set. Self-review parser bypasses, error context, imports, and mutable defaults. Commit with `git add` restricted to the task files and `git commit -m "Add strict typed document loading"`.

## Task 2: Bound documents, native styles, actions, and custom hosts

**Files:** Update `textui/document.py`, `__init__.py`; replace `textui/textui.py`; create `actions.py`, `styling.py`, `tests/test_runtime.py`, `tests/test_styles.py`, `tests/test_actions.py`, `tests/test_extensions.py`. Remove unused legacy widget/defs/CSS implementation if Task 1 leaves any, with evidence no new import uses it.

**Consumes:** Task 1's exact nodes/registry/error interfaces and DocumentLoader. Read the task report for field details before implementing; the spec takes priority over any implementation convenience.

**Produces:** Document.bind(App, actions=...), BoundDocument.compose/get_by_id/dispatch, ActionContext, TextUI convenience, atomic native TCSS integration, extension proof.

- [ ] Write and run failing runtime tests before code. Example:

```python
@pytest.mark.asyncio
async def test_bound_document_builds_typed_native_tree():
    import textui
    assert hasattr(textui, "TextUI"), "The new convenience App is missing"
    doc = textui.DocumentLoader().from_string(
        '<ui><vertical id="box"><checkbox id="flag" value="false">[x]</checkbox></vertical></ui>'
    )
    app = textui.TextUI(doc)
    async with app.run_test():
        flag = app.document.get_by_id("flag")
        assert flag.parent is app.document.get_by_id("box")
        assert flag.value is False
```

Tests cover six native widgets, multiple roots, classes/literal brackets, no generated IDs, get_by_id absent/pre-mount/removed cases, repeated compose/bind rejection, independent App instances, factory exceptions/wrong return/reused or mounted widget, and immutable action mapping. Native Pilot tests click buttons, change/submit input, and change checkboxes; exercise sync/async callbacks, exact custom message type/source, callbacks that raise, missing bindings, and no automatic stop/prevent. Verify initialization semantics rather than assuming no initial Changed events.

Style tests assert computed values for host CSS + embedded blocks + inline styles, `!important`, specificity, native valid properties previously discarded, theme variables, malformed CSS/inline variables, source context, no partial stylesheet installation after failed construction or parsing, and one-time style registration. Existing App integration forwards messages explicitly. One custom component uses typed attrs and a custom message forwarded by a host @on method.

- [ ] Run `.venv/bin/python -m pytest tests/test_runtime.py tests/test_styles.py tests/test_actions.py tests/test_extensions.py -q` and retain expected RED evidence.
- [ ] Implement bind validation without widget/style side effects; enforce one binding per App. Runtime constructs a whole tree before yielding, applies common attrs, rejects instance reuse, retains source context on construction errors, and has a well-defined failed/single-use state. Stage whole stylesheets with `.copy()` and stable `read_from` identities, then commit only after all construction succeeds. Inspect Textual's actual native parse/cascade APIs before choosing precedence plumbing; do not duplicate a CSS grammar. Tokenize inline variables with the native tokenizer; use `set_styles` for declarations. Message dispatch keys by exact type plus widget identity, awaits awaitable results, and raises ActionExecutionError from original failures.

```python
@on(Button.Pressed)
@on(Input.Changed)
@on(Input.Submitted)
@on(Checkbox.Changed)
async def forward_document_message(self, event):
    await self.document.dispatch(event)
```

Do not catch errors and return success. Core imports must remain image-free. Follow the spec's explicit lifecycle; do not add reload/remount support. Keep modules cohesive instead of introducing an event framework.

- [ ] Run all new tests to GREEN, inspect broad API consistency, then commit `Implement native document runtime and actions`. Report any tested native constraint that forced a spec interpretation.

## Task 3: Release packaging, examples, migration, and Python matrix

**Files:** Update `pyproject.toml`, `poetry.lock`, `README.md`, `AGENTS.md`, approved spec status; create `docs/migration.md`, `examples/editor.py`, `examples/form.xml`, `.github/workflows/tests.yml`, `tests/test_examples.py`; remove obsolete sample markup and image assets only if no retained example/docs references them (do not touch original checkout edits). Prefer replace the tracked old sample with a valid six-widget example and remove obsolete image references; do not add an image implementation in this task.

**Consumes:** Complete validated API from Tasks 1–2. No public behavior change without its regression test.

**Produces:** Version 0.2.0 build/install, accurate docs, runnable host/action example, CI and local matrix results with exact versions.

- [ ] Write a failing example test before introducing the example. Load the actual XML fixture, run the actual example App headlessly, drive its Save button, and assert a visible status label changes with the input value. Do not merely assert files exist or inspect source text. Test an installed wheel in a clean environment without imaging packages by importing core and running a minimal DocumentLoader/TextUI headless flow.

```python
@pytest.mark.asyncio
async def test_editor_save_updates_status():
    from examples.editor import Editor
    app = Editor()
    async with app.run_test() as pilot:
        app.document.get_by_id("name").value = "notes"
        await pilot.click("#save")
        assert "notes" in str(app.document.get_by_id("status").render())
```

- [ ] Update dependencies to the Global Constraints, use compatible contemporary pytest/pytest-asyncio test constraints, configure deterministic headless test collection, and generate a real Poetry lock using Poetry compatible with its format in an isolated tool environment. Do not hand-edit lock resolution. Set pytest async defaults explicitly to avoid future-warning noise. Remove mandatory imaging dependencies. Set version 0.2.0 and useful project description.
- [ ] Implement a runnable `python -m examples.editor` example with a source-relative XML path and registered action that updates a Label. README documents install, test/build/run commands, normal App integration, custom factory/event contract, trust/lifecycle/style limits, and links migration/spec. Migration covers old constructor/root/scripts/classes/tag aliases/query helpers/TCSS behavior. Update AGENTS commands to actual new workflow. Mark spec approved and implemented subject to gates; record exact validation evidence separately if useful.
- [ ] Run `.venv/bin/python -m pytest -q`; resolve concrete new failures with regression coverage. Create isolated Python 3.11 and 3.14 environments, install the project and declared test dependencies, run the same suite on all three interpreters. Build and install a wheel outside the repo, run `pip check`/equivalent, and verify no PIL/textual_imageview import/install occurs. Record versions and full results in the task report. Keep tooling/venvs ignored.
- [ ] Add CI for Python 3.11/3.12/3.14 with official supported checkout/setup-python actions and install/test/build steps. Inspect official action versions before choosing refs. Commit `Package and document the TextUI core reboot`.

## Completion gates

- Each task receives independent spec/quality review; fix important issues before downstream use.
- Run a final whole-branch review against the approved specification, including custom extensions, error/lifecycle behavior, and dependency/image boundary.
- Preserve the original dirty checkout. Do not publish or push automatically. Deliver the clean committed implementation branch and exact test results; integrate locally only if doing so preserves the original edits without an ambiguous conflict.
- Record any necessary rulings and residual limitations. No new user approval is required for routine implementation choices or moving between tasks; the owner explicitly authorized autonomous continuation.
