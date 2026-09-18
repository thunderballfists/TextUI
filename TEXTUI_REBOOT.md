# TextUI Reboot Brief

Status: design handoff, 2026-09-17

## North star

TextUI should be a lightweight declarative authoring layer for Textual, not a
new terminal renderer or a competing widget framework.

The intended division of responsibility is:

- markup defines structure;
- TCSS defines appearance;
- Python defines behavior;
- Textual supplies widgets, layout, rendering, events, async execution, testing,
  terminal input, and browser delivery.

In one sentence:

> TextUI lets developers describe a Textual interface as validated markup while
> retaining normal Python for application behavior.

## Why revisit it now

The original project began in 2023 from a useful observation: Textual already
has a DOM-like widget tree, CSS, selectors, events, and components, but no
first-class HTML-like document format. TextUI filled that authoring gap rather
than replacing Textual's runtime.

Textual is substantially more capable now. A reboot can inherit its mature
widgets and tooling while keeping TextUI narrowly focused on parsing,
validation, component registration, and declarative event wiring.

Declarative documents are also easier than generated Python to inspect,
validate, constrain, and generate mechanically. That could eventually make
TextUI useful for machine-generated interfaces, but generated-UI security is
not a phase-one deliverable.

## Current repository baseline

The repository contains a small working prototype, not an empty experiment.

| Area | Current implementation |
| --- | --- |
| Application/parser | `textui/textui.py` parses markup, composes widgets, adds embedded and inline styles, and runs collected scripts. |
| Widget registry | `textui/widgets/widget_factory.py` maps tags through `ElementWidgetDefinition`. |
| Built-in mappings | `textui/widgets/builtin_widgets.py` exposes many Textual containers and widgets. |
| HTML-like elements | `textui/widgets/html_widgets.py` implements `div`, `p`, `span`, and image support. |
| DOM-like facade | `textui/document.py` wraps Textual queries and event attachment. |
| CSS filtering | `textui/validate_css.py` validates and reconstructs a subset of TCSS. |
| Tests | Seven tests cover scripts, multiple style tags, and parts of CSS validation. |

The project currently declares Python `^3.11`, Textual `^3.3.0`,
`textual-imageview`, and `lxml`. With a clean Python 3.12 environment, pip
resolved Textual 3.7.1 and all seven existing tests passed on 2026-09-17. The
current Textual constraint is below 4.0, so this result says nothing about
Textual 8.x compatibility.

The latest stable Textual release was 8.2.8 when this brief was written. Verify
the current release before changing dependency constraints.

## What is worth preserving

- Building on Textual instead of reimplementing terminal rendering.
- A registry between markup tags and widget construction.
- External markup files and markup strings.
- Embedded and inline TCSS as authoring conveniences.
- DOM-like lookup conveniences where they add value over raw Textual queries.
- Extensibility: applications should be able to register their own components.
- The small, understandable package structure.

Preserve the concepts, not necessarily the current implementation or public
API. Compatibility should be an explicit decision after the audit, not an
assumption.

## Architectural direction

### 1. A typed component registry

Evolve `ElementWidgetDefinition` from a tag/class/preprocessor tuple into
metadata that knows how a component is constructed.

Conceptually, a definition may describe:

- tag name and widget/component class;
- allowed attributes and their converters;
- text and child-content rules;
- supported events and their message classes;
- optional custom construction logic;
- whether child widgets are permitted;
- dependency or capability requirements, such as image support.

Do not assume every Textual widget can be built with
`widget_class(text, **attributes)`. Constructor adapters should be explicit and
testable.

### 2. Declarative actions instead of embedded Python by default

Arbitrary `<script>` execution currently makes a markup document executable
code. The normal event model should instead refer to Python actions registered
by the host application, for example:

```xml
<button id="save" on-pressed="save_document">Save</button>
```

```python
@ui.action("save_document")
def save_document(event):
    ...
```

The exact decorator/API is not decided. The important boundary is that markup
selects from actions the application deliberately exposed. A separately named
trusted-script mode could be considered later, but should not be the default or
required for ordinary event handling.

### 3. First-class custom components

Applications should eventually be able to register domain-level components:

```xml
<server-status host="east" refresh="5" />
<job-table source="production" />
```

The registry should treat built-in Textual widgets and application-defined
components through the same core abstraction where practical.

### 4. Useful failures

Invalid markup should fail deterministically with source context. Errors should
identify the element and attribute involved instead of silently omitting an
unknown tag or surfacing an unrelated constructor `TypeError`.

The parser should define behavior for:

- unknown elements and attributes;
- duplicate IDs;
- invalid nesting or child content;
- invalid attribute conversions;
- unknown actions and events;
- unsupported optional features;
- malformed TCSS.

Strict behavior should be the default. A permissive mode is optional and needs
a concrete use case before implementation.

## Specific issues to audit before redesigning

These are observations and investigation targets, not preselected fixes:

1. `parse_markup()` iterates over the parsed root's children, so the root acts
   as an implicit document wrapper rather than a rendered component. Decide
   whether that is intentional and document the grammar.
2. Parsing mutates `element.attrib` by removing `style` and `class` and adding
   generated IDs. Repeated parsing may therefore be stateful or surprising.
3. The generic factory assumes text is the first positional constructor
   argument and forwards all attributes unchanged. Textual widget constructors
   do not share that contract.
4. Unknown tags currently disappear without an error.
5. The hand-maintained CSS validator duplicates Textual's evolving TCSS
   grammar and is likely to drift. Investigate whether Textual can parse or
   validate TCSS directly, and separately decide whether TextUI needs an
   allowlist for untrusted documents.
6. `<script>` ultimately uses `exec`. The README describes `document` and
   `window` helpers, while the execution globals expose only `app` directly.
7. Verify `Document.add_event_listener()` against current Textual event APIs.
8. Class handling, nested composition, widgets with special construction
   requirements, and source-location errors need focused tests.
9. Image support makes Pillow and `textual-imageview` mandatory. Prefer a core
   package with an optional image extra if the current image approach remains
   viable.
10. Determine whether `lxml` provides necessary behavior. A constrained markup
    language may be supportable with a standard-library parser, reducing binary
    dependencies and install size.
11. Establish a tag and attribute naming convention. The prototype uses names
    such as `horizontal_scroll`; HTML-like kebab-case may be more natural, but
    compatibility and clarity should drive the decision.

## Non-goals for the first implementation phase

- A new terminal renderer or widget toolkit.
- Browser HTML compatibility or a JavaScript runtime.
- A general-purpose templating language.
- Reactive data binding comparable to Vue, React, or QML.
- A complete HTML or CSS standard.
- Preserving every prototype API at the expense of a coherent design.
- A security claim for untrusted or LLM-generated documents before an explicit
  threat model and allowlist design exist.

## Suggested sequence

This is a discovery sequence, not an implementation plan.

1. **Baseline and compatibility audit**: reproduce current tests, test the
   current stable Textual release, catalog failures and API changes, and inspect
   what Textual now provides directly.
2. **Minimal core design**: define the document grammar, typed registry,
   construction adapters, error model, and smallest supported widget set.
3. **Core implementation**: parse and render a representative document on the
   selected Textual version, with deterministic errors and focused tests.
4. **Actions/events**: add registered Python actions without requiring embedded
   code.
5. **Custom components**: support reusable application-defined elements and
   nested composition.
6. **Optional capabilities and tooling**: reconsider images, schema/editor
   assistance, compatibility helpers, and safe machine generation only after
   the core model is stable.

## Questions the audit should answer

- Is this a clean break for a pre-1.0 prototype, or is any compatibility worth
  preserving?
- Which current Textual APIs can replace custom code, especially TCSS parsing,
  event attachment, and component composition?
- Should TextUI subclass `App`, wrap an existing `App`, or provide both an app
  convenience and a lower-level document loader?
- What is the smallest widget/component set that proves the architecture?
- Which parser best balances source locations, dependency size, XML-like
  syntax, and safe defaults?
- What should be validated by TextUI versus delegated to Textual?
- How should registered actions receive their event, widget, app, and document
  context?
- What public extension API can remain small while supporting custom
  components?

## First-session deliverable

Before changing production code, produce a concise repository audit containing:

1. the verified baseline and dependency versions;
2. Textual 8.x compatibility failures grouped by root cause;
3. code that can be retained, adapted, or removed;
4. two or three viable architectural approaches and their tradeoffs;
5. a recommended minimal architecture;
6. unresolved decisions requiring owner input;
7. a staged implementation plan with testable milestones.

The audit should challenge this brief where the repository or current Textual
APIs provide better evidence. Do not preserve an old mechanism merely because
it already exists.

## Reference links

- Repository: <https://github.com/thunderballfists/TextUI>
- Textual documentation: <https://textual.textualize.io/>
- Textual releases on PyPI: <https://pypi.org/project/textual/>
