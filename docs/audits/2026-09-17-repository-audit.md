# TextUI repository audit

Date: 2026-09-17. Audited commit: `d359800` (including upstream `6b72d42`).
Status: findings and recommendations for approval; no implementation or design specification.

## Recommendation

Proceed with a small pre-1.0 redesign: a document loader with explicit typed component definitions, native Textual styling, and registered Python actions. Provide an optional `TextUI(App)` convenience over that loader. Start with six widgets and a strict document grammar.

The immediate problem is correctness, not a demonstrated Textual 8 migration failure. All seven committed tests pass on both Textual 3.7.1 and 8.2.8, but focused probes expose substantial defects on both. The shipped sample fails during composition. Preserve the useful authoring model and replace the assumptions that every widget has the same constructor, every markup attribute is a string constructor argument, and TCSS needs a separate regex validator.

## Evidence and environments

The latest stable release is **Textual 8.2.8**, uploaded on 2026-06-30, verified against PyPI metadata and the official release notes on the audit date. The brief's version is still current. [PyPI](https://pypi.org/project/textual/8.2.8/), [release notes](https://github.com/Textualize/textual/releases/tag/v8.2.8).

All experiments used disposable environments and repository copies outside the working tree. The committed source and the working copy were tested separately because `tests/test_markup.py` is untracked and `examples/sample_markup.xml` has a local modification.

| Environment | Python | Textual | lxml | Pillow | Rich | pytest / pytest-asyncio | Result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Lockfile package versions | 3.11.4 | 3.3.0 | 4.9.2 | 9.5.0 | 13.3.3 | 7.2.2 / 0.21.0 | 7 committed tests passed |
| Fresh resolution of declared constraints | 3.12.5 | 3.7.1 | 4.9.4 | 12.3.0 | 15.0.0 | 7.4.4 / 0.21.2 | 7 committed tests passed; 8 working-copy tests passed |
| Current stable comparison | 3.12.5 | 8.2.8 | 4.9.4 | 12.3.0 | 15.0.0 | 7.4.4 / 0.21.2 | 7 committed tests passed; 8 working-copy tests passed |

`textual-imageview` was 0.1.1 in every environment. All three dependency environments passed `uv pip check`. The baseline package also built and installed successfully. The lockfile environment was reconstructed from its package pins, excluding Windows-only colorama, rather than installed through Poetry; lxml 4.9.2 required a local build. The current comparison deliberately imported the unchanged source without installing TextUI's package metadata, which correctly excludes Textual 8 via `^3.3.0`.

The local eighth test forces `headless=False`, writes a screenshot, and contains no assertions. Its pass is a smoke result, not evidence of correct appearance. Seven committed tests exercise four script cases, one multiple-style case, and two CSS cases. These tests do not run a normal mounted application lifecycle.

Additional probes compared parsing, construction, mounting, styles, queries, scripts, events, and images. A nested Vertical/Button tree mounted successfully; a native asynchronous `@on(Button.Pressed)` handler received one simulated click; an image without dimension attributes mounted and resized successfully in both comparison environments. These are bounded compatibility results, not certification of every registered widget or terminal.

## Actual architecture and behavior

- **Application and input:** `TextUI` subclasses `App` and owns parsing, construction, styling, script execution, and query helpers. A string is treated as a path only if that file exists; otherwise it becomes markup. Missing-file errors are therefore ambiguous. There is no independent loader for an existing app.
- **Document root:** `lxml.html.fromstring()` builds a forgiving HTML tree; `parse_markup()` renders only its children. Root attributes and root widget identity disappear. A single `<label>Hello</label>` renders nothing. An `<html>` root also produced nothing in the probe because HTML parsing inserts an unsupported wrapper.
- **Nested widgets:** children are attached with `compose_add_child()`. Ordinary nested containers work. There is no meaningful child-content policy: the presence of that inherited method does not establish that a particular widget should accept arbitrary children. Text is collapsed to one space and supplied as the first positional argument; tail text is ignored.
- **Registry:** 36 built-in mappings plus seven HTML/directive definitions connect lowercase tags to a class and optional preprocessor. Registration silently replaces an existing tag. There are no converters, required-attribute checks, event schemas, or source-aware errors. `ElementWidgetDefinition.app` is unused.
- **IDs/classes:** almost every widget receives a random UUID ID unless supplied explicitly; Footer is special-cased. `class="one two"` is passed as one class name and rejected. IDs duplicated among siblings fail during mounting, while identical IDs in separate branches mounted successfully. Document-wide uniqueness is not enforced.
- **Styles:** embedded blocks pass through the custom CSS filter and then Textual's stylesheet parser, using fresh UUID source names. Inline styles synthesize ID selectors, except Footer, and call an obsolete keyword. Image dimensions use that same inline path. External TCSS files are not loaded by this markup layer.
- **Scripts:** preprocessing queues Python; `on_mount()` executes it in order with unrestricted Python builtins and `app`. Each block receives a fresh globals dictionary. `app.document` and `app.window` exist; bare `document` and `window` do not. Exceptions are logged and suppressed; unsupported languages are skipped.
- **Queries/events:** mounted ID and class queries work. The plural ID method wraps at most one match and catches every exception. The document tag helper forwards markup names directly to Textual selectors, although Textual expects names such as `Button`, not `button`. `add_event_listener()` calls nonexistent `widget.on()`.

The brief's mutation warning needs refinement: `parse_markup()` reparses the string into a fresh tree each time, so stripped attributes are not reused by that path. Reusing an element through `parse_element()` does lose its classes. Repeated composition also changes generated IDs, accumulates embedded styles, and queues scripts again. Those side effects are the more relevant lifecycle risk.

## Failures grouped by root cause

Every failure below was reproduced on **both 3.7.1 and 8.2.8**. No new 8.2.8-only failure emerged from these probes.

| Root cause | Reproduction and consequence | Direction |
| --- | --- | --- |
| Outdated stylesheet integration | `<label style="color: red;">Hi</label>` raises `TypeError` because `Stylesheet.add_source()` accepts `read_from`, not `path`. Both committed and locally edited sample documents fail through image dimensions. | Replace the inline path; isolate whole-stylesheet integration behind a small adapter. |
| Untyped construction | `<p>Hello</p>` passes a string as a Widget child and fails. `<tree/>` lacks its required label. `disabled="false"` remains a truthy string. Unknown event attributes become unexpected constructor arguments. | Explicit converters, text rules, required attributes, and constructor adapters. |
| Incorrect class handling | Two space-separated classes raise `BadIdentifier`. | Split and validate class tokens or use Textual's constructor `classes` argument. |
| Forgiving parsing plus silent omission | Malformed markup is repaired; unknown tags drop their entire subtree; a comment node crashes `.tag.lower()`. | Explicit XML grammar and deterministic diagnostics. |
| Lossy TCSS filtering | Valid `height: auto`, `width: 1fr`, `align: center middle`, and `text-wrap: wrap` disappear. `$gap: 1; ... padding: $gap 2` is changed to `padding:$gap`. Invalid prose becomes empty CSS. | Delegate TCSS grammar and errors to Textual. |
| Incorrect helper API/lifecycle assumptions | `add_event_listener()` raises `AttributeError`; lowercase tag queries raise `InvalidQueryFormat`; README lookups before mounting raise `ScreenStackError`. | Native handlers plus a document-scoped lookup facade with clear lifecycle. |
| Executable markup and hidden errors | Bare script helpers raise logged `NameError`; arbitrary imports and builtins remain available. | Registered action names; reject scripts in the new default grammar. |

Textual already exposes `set_styles()` for literal inline declarations, and its stylesheet implementation accepts source locations. Native inline parsing rejected an unknown property while accepting the valid declarations discarded by TextUI. One boundary matters: `set_styles("color: $text;")` also fails in both tested versions; it does not resolve app theme variables automatically. Initially restrict inline styles to literal declarations and put variable-dependent styling in whole TCSS stylesheets. [DOM API](https://textual.textualize.io/api/dom_node/#textual.dom.DOMNode.set_styles), [8.2.8 stylesheet source](https://github.com/Textualize/textual/blob/v8.2.8/src/textual/css/stylesheet.py).

Native event handlers use methods or the `@on` decorator; bubbling supplies the route from child controls to a host. Use those mechanisms instead of assuming a JavaScript-style dynamic listener API. Keep any bridge limited to explicitly supported messages and test custom-message adapters. [Events and messages](https://textual.textualize.io/guide/events/).

## Test and documentation gaps

The main CSS test computes its expected output by calling the function under test during collection. It checks repeatability, not correctness. The uppercase-color test checks preservation by the custom filter but never asks Textual to apply the result. The style test checks stored source contents, not computed widget styles. The script tests call `compose()` and `on_mount()` manually, without establishing normal widget mounting.

Missing tests cover root semantics, comments, malformed documents, unknown attributes/tags, conversion of booleans/numbers/enums, mixed content, constructor-specific requirements, classes, inline TCSS, duplicate IDs, missing files, remount/reload behavior, query lifecycle, real button/input messages, custom components, image dimensions, and actionable error locations. Add headless `run_test()`/Pilot checks and direct style assertions; snapshots alone would not catch most of these. [Textual testing guide](https://textual.textualize.io/guide/testing/).

The README calls scripting future work while code executes scripts today; uses undefined `MyApp`; performs lookups before mounting; promises unavailable bare script globals and a broken listener method; and describes tag queries without the tag/type distinction. It claims inline styling despite the reproduced failure. The module entry point also assumes `../examples/...` relative to the process directory, making repository-root module execution unreliable. The local `onclick="handle_click"` example has no matching implementation and would fail construction after the earlier image failure is fixed.

History explains the partial migration: commit `5c3f17a` adapted embedded styles to `read_from` during the Textual 3.3 update but left inline styles using `path`. Later script execution exposes only `app`, despite helper documentation. These are incomplete integration changes, not reasons to recreate Textual's runtime.

## Retain, adapt, remove

| Retain conceptually | Adapt | Remove from the new default core |
| --- | --- | --- |
| Textual runtime; external documents and strings; tag registry; native nesting; Python extensions | Explicit file/string entry points; typed component definitions; native styling; small mounted-document lookup interface; optional app convenience | Regex TCSS parser; default `exec`; fabricated listener API; universal constructor forwarding; silent dropping/repair; unnecessary generated IDs; mandatory image imports |

The image implementation is not proven incompatible with current Textual: mounting and resizing worked when the broken dimension path was absent. Keep it as a candidate optional extra, with independent tests, rather than rewrite it preemptively. The `div`/`p`/`span` classes provide styling but do not implement HTML text flow; omit them from the initial supported vocabulary instead of promising HTML behavior.

## Architecture options

| Option | Registry, actions, diagnostics, custom components | Tradeoff |
| --- | --- | --- |
| **A. Loader plus optional App convenience — recommended** | Explicit immutable component specs describe attribute converters, text/child policies, factories, and supported messages. Parse to source-located nodes, validate, then construct. An explicit host adapter routes native messages to exposed callables. Custom factories use the same registry. | More initial separation, but reusable inside ordinary Apps/Screens and independently testable. Styling and handler lifetime need explicit contracts. |
| B. Expand the existing App subclass | App-owned definitions/decorators register typed factories and exposed action methods. Validation runs before `compose`; the app owns styles and native message handlers. Custom components return widgets. | Fastest small prototype, but forces consumers into TextUI's lifecycle and makes multiple documents or existing apps harder to integrate. |
| C. Wrap an existing App with component adapter classes | A controller manages document loading while each registered adapter implements construction, validation, and event forwarding; source locations travel with adapter input. Host-supplied callbacks define actions. | Flexible host integration, but more boilerplate and complicated attachment/cleanup. Transparent wrapping risks private message interception and conflicts with host composition. |

Prefer A. Keep the loader independent; allow a thin App subclass for one-file demos. Do not make a transparent wrapper over an arbitrary running App the primary API. Require explicit host integration. Avoid constructor introspection as the schema: Python signatures do not specify markup semantics, safe capabilities, text handling, or valid children.

## Recommended minimal boundaries

1. **Grammar and loader:** explicit `from_file`/`from_string` concepts; one non-rendered `<ui>` wrapper; lowercase kebab-case tags/attributes; reject unsupported content rather than repair it. Preserve source filename, node line, tag, attribute, and offending value. Define text-only leaves and child-only containers; defer general mixed content.
2. **Registry and validation:** a small dataclass-based specification with converters, required/default values, enum constraints, text policy, child policy, supported events, and a factory. Check duplicate registrations and document IDs. Validate the entire document before widget construction/mounting; wrap constructor errors with source context. No Pydantic or schema framework is justified yet.
3. **Construction and styling:** return normal Textual widgets with fresh instance state. Use native container child construction where supported and explicit adapters elsewhere. Keep stable source identities for embedded styles and a narrow Textual integration adapter for whole TCSS. Use native inline declarations without UUID selector generation. Define stylesheet precedence and initial lifetime as one loaded document per host; defer hot reload and multiple independent stylesheet scopes.
4. **Actions:** `on-pressed="save_document"` selects an entry in a host-provided mapping. Do not evaluate expressions, resolve arbitrary methods, or import dotted names from markup. Support sync/async callbacks with one context object containing event, source widget, app, and document. Start with native handlers for supported control messages. Custom components may supply an explicit native event adapter; arbitrary-message routing is a later extension test, not an excuse to hook private dispatch internals.
5. **Smallest proof:** `vertical`, `horizontal`, `label`, `button`, `input`, and `checkbox`; the `<ui>` and `<style>` directives are not widgets. These demonstrate nesting, text, string/bool/enum conversion, and pressed/changed/submitted messages. Add one application-defined status component through the same factory contract. Defer tables, trees, tabs, images, and HTML aliases.

Example diagnostic shape: `form.xml:12 <checkbox> attribute 'value': expected true or false; got 'maybe'`. Syntax and semantic errors should be distinguishable; TCSS errors should preserve Textual's explanation and map back to the embedded block.

## Parser, dependency, and trust decisions

**Retain lxml initially, but use strict XML rather than the HTML parser.** Its node source lines and parser diagnostics support the desired errors immediately; a probe verified line retention. Explicitly configure non-recovering parsing, disable entity resolution and DTD loading, disallow DTD/entity content, and do not invoke XInclude. Treat these as parser constraints, not an untrusted-input safety guarantee. Review the supported lxml version during implementation instead of preserving the old major indefinitely. [lxml parser and element API](https://lxml.de/apidoc/lxml.etree.html).

Standard-library ElementTree can handle the tree grammar, but does not expose a documented source position on each ordinary element. A SAX/Expat builder can preserve positions at the cost of more loader code. Choose that route only if eliminating the binary dependency is a firm product requirement; it is not currently necessary to reduce architectural complexity. [ElementTree](https://docs.python.org/3/library/xml.etree.elementtree.html), [Expat positions](https://docs.python.org/3/library/pyexpat.html).

Target the tested current Textual release for the reboot, with an explicit supported range after Python-minimum and integration checks. Preserve Python 3.11 as the proposed minimum, but note that the current-release experiments here used 3.12.5. Remove the custom TCSS grammar and move Pillow/textual-imageview behind an optional image capability. No dependency file was changed during this audit.

The initial trust model should be **developer-authored documents and trusted application registrations**. Removing scripts prevents automatic embedded Python execution, but registered factories/actions can still read files, use networks, or perform destructive work. A future untrusted-document mode needs enforceable component/action/property allowlists, resource-path restrictions, document/depth/resource limits, and a separate execution/capability analysis. No such security claim is justified now.

## Staged implementation proposal

| Stage, after approval | Acceptance evidence |
| --- | --- |
| 1. Characterization and support policy | Add meaningful regression cases for the reproduced failures; choose Python/Textual range; run CI on minimum Python and a current Python; document intended compatibility breaks. |
| 2. Grammar and validation | File/string parsing, root rules, source locations, comments, typed values, unknown names, duplicate IDs, text/child rules, and missing files have deterministic tests. Parsing has no application side effects. |
| 3. Minimal rendering and TCSS | Six widgets render inside a normal host and the optional App. Assert parentage, classes, computed styles, malformed TCSS diagnostics, independent document instances, and the agreed style lifetime. |
| 4. Registered actions | Pilot clicks, changes, and submissions invoke only exposed callbacks; test sync/async handlers, unknown action/event rejection, error propagation, and no duplicate invocation after lifecycle transitions. |
| 5. Custom component contract | Register an application component with typed attributes, native children, and a declared message adapter without editing core; verify actionable extension errors. |
| 6. Packaging and examples | Core installs without imaging dependencies; optional image tests cover load/resize/dimensions. Replace README examples with tested, runnable examples and document migration. |

No hot reload, template expressions, reactivity layer, browser HTML compatibility, renderer, or JavaScript runtime is needed to prove this design.

## Reproduction and retained evidence

Temporary audit directory on this machine:

`/var/folders/03/k0dx8m0x1b165mk5gfsjg4mm0000gn/T/textui-audit-20260917-jw_b6woh`

It contains the `tracked` and `working` snapshots; `locked`, `baseline`, and `current` environments; installation logs; exact `*-freeze.txt` files; five test-result logs; PyPI metadata; and throwaway `probe.py`/`followup.py` scripts with per-environment JSON and stderr output. Temporary evidence is not a permanent test suite and may be removed by the operating system.

Core reproduction commands, using those existing snapshots:

```sh
AUDIT_ROOT=/var/folders/03/k0dx8m0x1b165mk5gfsjg4mm0000gn/T/textui-audit-20260917-jw_b6woh
cd "$AUDIT_ROOT/tracked"
"$AUDIT_ROOT/baseline/bin/python" -m pytest -q -p no:cacheprovider
"$AUDIT_ROOT/current/bin/python" -m pytest -q -p no:cacheprovider
"$AUDIT_ROOT/locked/bin/python" -m pytest -q -p no:cacheprovider
"$AUDIT_ROOT/current/bin/python" "$AUDIT_ROOT/probe.py" "$AUDIT_ROOT/tracked"
"$AUDIT_ROOT/current/bin/python" "$AUDIT_ROOT/followup.py" "$AUDIT_ROOT/tracked"
```

Fresh baseline installation used the snapshot's package metadata plus `pytest>=7.2.2,<8` and `pytest-asyncio>=0.21.0,<0.22`. The comparison environment installed `textual==8.2.8`, `textual-imageview>=0.1.1,<0.2`, and `lxml>=4.9.2,<5`, with the same test constraints. Other resolved packages matched between the comparison environments. Application code, tests, dependencies, APIs, and pre-existing working-copy edits were unchanged.

Limits: no visual snapshot comparison, browser-serving test, exhaustive widget matrix, cross-platform test, or untrusted-input security assessment was performed. No new Textual-8-specific failure was observed within the tested scope.

## Decision checklist

- [x] Approve a pre-1.0 grammar/API break, or identify consumers that require compatibility.
- [x] Choose loader plus optional App convenience (recommended) versus an App-only product.
- [x] Accept strict `<ui>` XML, kebab-case names, and retaining lxml initially; otherwise make a standard-library-only parser a requirement.
- [x] Approve registered actions with one context argument, six initial widgets, optional images, and rejection of scripts in the default grammar.
- [x] Accept literal inline styles initially, with variables in TCSS stylesheets; confirm one document per host is sufficient for the first proof.

The owner approved all five recommended decisions on 2026-09-17. The resulting [core design specification](../superpowers/specs/2026-09-17-textui-core-design.md) is the next review checkpoint before implementation planning.
