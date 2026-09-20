# TextUI Extension Triage and Delivery Order

Date: 2026-09-19
Updated: 2026-09-20

## Direction

TextUI has completed the original runtime-data, layout, dialog-lifecycle, command, and visual-regression work. The next work should add one useful application capability at a time through the existing markup, controller, and registry boundaries. Markup declares structure, TCSS controls presentation, and included Python supplies data and behavior.

This is a proposed roadmap, not a commitment to install the referenced libraries.

## External Projects

| Project | Useful ideas | Adoption approach |
| --- | --- | --- |
| [TextTUI](https://github.com/kdp1965/texttui) | Compact dashboards, control grouping, plotting | Visual reference. Its README targets pre-TCSS Textual 0.1.14. |
| [textual-enhanced](https://github.com/davep/textual-enhanced) | Confirmation/input dialogs, command metadata, preserving selection during refresh | Strongest implementation reference. Adapt selected patterns or evaluate an optional adapter for a specific widget. |
| [Textology](https://github.com/pyranha-labs/textology) | Observation, routing, richer selection, visual testing | Design reference. Its current dependency pin conflicts with TextUI's Textual 8 requirement. |

Compatibility evidence: TextUI requires `textual>=8.2.8,<9`; [Textology requires `textual>=0.85.0,<0.86.0`](https://github.com/pyranha-labs/textology/blob/main/requirements.txt). [textual-enhanced declares `textual>=1.0.0`](https://github.com/davep/textual-enhanced/blob/main/pyproject.toml), which permits Textual 8 but does not prove runtime compatibility. Its concrete offerings focus on dialogs, commands, option-list navigation, and text viewing; the earlier suggestion that it could supply enhanced tables was too broad.

Use native Textual capabilities first, small TextUI adapters second, and optional third-party dependencies for specialist features. If copying source rather than independently implementing an idea, retain the upstream license and attribution.

## Completed from the original triage

[Issue #28](https://github.com/thunderballfists/TextUI/issues/28) is closed. The original table contract now provides markup columns, runtime `set_rows()` replacement, stable row keys, record lookup, column metadata, and header-click sorting that persists when rows refresh. The data example exercises the API.

- Lifecycle and visual regression coverage now checks repeatable modal behavior, cleanup, shell geometry, pointer reachability, and opt-in visual baselines.
- Compact and border style presets are implemented and may be switched at runtime.
- Modal lifecycle behavior, shared commands, shortcuts, async lifecycle targets, and shutdown cancellation are implemented.
- Reusable local components support imports, literal properties, named slots, fallback content, and isolated template IDs.

The historic implementation plans remain as engineering records. Their unchecked task lists do not indicate unfinished shipped work.

## Remaining roadmap

| Order | Deliverable | Scope and rationale |
| --- | --- | --- |
| 1 | Dashboard widgets | Add a native `<sparkline>` adapter for compact numeric trends. Keep full line/bar/scatter charts as an optional plotting extension, driven by a real dashboard requirement. |
| 2 | Selection and state presentation | Add a `selection-list` adapter and reusable loading, empty, and error presentation patterns. These fill practical control gaps without adding a reactive template language. |
| 3 | Command surfaces | Build menus or a command palette on the existing `@command` metadata when an application needs them. Dynamic enabled predicates and user-configurable shortcuts remain separate design work. |
| 4 | Reactive navigation | Define observation, refresh, routing, and history only after a project demonstrates the need beyond the existing content switcher, runtime lists, and tables. |
| 5 | Dynamic component authoring | Consider reactive properties, repetition, conditional templates, component-local styles, and a component registry together. Do not introduce expressions or embedded Python as an incremental shortcut. |

## Explicitly deferred boundaries

- Core remains strict XML with linked Python; there is no expression evaluation, embedded Python, automatic data binding, or browser HTML compatibility.
- Hot reload, recomposition, document replacement, multiple stylesheet scopes, and aggregated validation diagnostics need separate lifecycle designs.
- Images and full plotting remain optional dependencies. Do not add Pillow, textual-imageview, Textology, or textual-enhanced to core.
- An untrusted-document mode requires enforceable capability limits and is not implied by strict XML validation.

## Specific Patterns to Study

- [Native SelectionList](https://textual.textualize.io/widgets/selection_list/) is the likely substrate for multiple selection, distinct from a dropdown multi-select.
- [Textual Sparkline](https://textual.textualize.io/widgets/sparkline/) is the preferred substrate for a first core trend widget.
- [Preserved option-list highlighting](https://github.com/davep/textual-enhanced/blob/main/src/textual_enhanced/widgets/option_list.py) remains a useful reference when adding stronger identity preservation to lists.
- [Confirmation dialog](https://github.com/davep/textual-enhanced/blob/main/src/textual_enhanced/dialogs/confirm.py) and [input dialog](https://github.com/davep/textual-enhanced/blob/main/src/textual_enhanced/dialogs/modal_input.py) remain references for a later higher-level dialog API.
- [Textology observation patterns](https://github.com/pyranha-labs/textology#top-features) are design references only; do not import its application runtime.
- Continue using [Textual testing](https://textual.textualize.io/guide/testing/) and the built-in `App.export_screenshot()` SVG comparison suite. `pytest-textual-snapshot` is incompatible with the supported pytest 9 range.

## Guardrails

- Python `>=3.11,<4`; Textual `>=8.2.8,<9`; lxml `>=6.1.3,<7`.
- Core must not depend on Pillow, textual-imageview, Textology, or textual-enhanced.
- Keep strict XML and explicit linked-Python actions; no expression evaluation or embedded Python.
- Preserve unrelated root-checkout changes; implementation uses an isolated worktree.
- Do not mark a visual problem fixed from object identity, `.visible`, or green CI alone. Verify a real hit target and inspect the rendered output.
