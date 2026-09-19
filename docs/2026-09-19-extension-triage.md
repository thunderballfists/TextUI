# TextUI Extension Triage and Delivery Order

Date: 2026-09-19

## Direction

Finish the runtime-data API in issue #28, then improve dialogs and commands. Adopt useful patterns through TextUI's existing markup, controller, and registry boundaries. Markup declares structure, TCSS controls presentation, and included Python supplies data and behavior.

This is a proposed roadmap, not a commitment to install the referenced libraries. Item 0 has an [implementation plan](superpowers/plans/2026-09-19-lifecycle-visual-regressions.md).

## External Projects

| Project | Useful ideas | Adoption approach |
| --- | --- | --- |
| [TextTUI](https://github.com/kdp1965/texttui) | Compact dashboards, control grouping, plotting | Visual reference. Its README targets pre-TCSS Textual 0.1.14. |
| [textual-enhanced](https://github.com/davep/textual-enhanced) | Confirmation/input dialogs, command metadata, preserving selection during refresh | Strongest implementation reference. Adapt selected patterns or evaluate an optional adapter for a specific widget. |
| [Textology](https://github.com/pyranha-labs/textology) | Observation, routing, richer selection, visual testing | Design reference. Its current dependency pin conflicts with TextUI's Textual 8 requirement. |

Compatibility evidence: TextUI requires `textual>=8.2.8,<9`; [Textology requires `textual>=0.85.0,<0.86.0`](https://github.com/pyranha-labs/textology/blob/main/requirements.txt). [textual-enhanced declares `textual>=1.0.0`](https://github.com/davep/textual-enhanced/blob/main/pyproject.toml), which permits Textual 8 but does not prove runtime compatibility. Its concrete offerings focus on dialogs, commands, option-list navigation, and text viewing; the earlier suggestion that it could supply enhanced tables was too broad.

Use native Textual capabilities first, small TextUI adapters second, and optional third-party dependencies for specialist features. If copying source rather than independently implementing an idea, retain the upstream license and attribution.

## Issue #28: Partly Complete

[Issue #28](https://github.com/thunderballfists/TextUI/issues/28) requests markup-declared columns and runtime rows for usage/cost API data. Its original statement that there is no `<data-table>` is outdated; the issue should remain open for the missing convenience API.

Existing support in `textui/widgets/data_widgets.py`:

- Declared columns and optional seed rows.
- Native `add_row()`, cell updates, scrolling, and selection.
- `row-selected` and `cell-selected` actions.

Remaining work:

- `set_rows()` accepting mapping records from APIs.
- Column `label`, `align`, and `width` attributes.
- Explicit replacement and selection behavior.
- Empty-state content.

Proposed contract, not currently implemented:

```xml
<data-table id="usage" row-key="date" on-row-selected="select_usage">
  <column key="date" label="Date" />
  <column key="requests" label="Requests" align="right" width="10" />
</data-table>
```

```python
window.document.get_by_id("usage").set_rows(records)
```

Column keys select record fields, while existing text-label syntax remains supported. Validate the entire batch before replacing displayed rows. Retain raw numeric values for sorting and format only for display. Preserve the cursor's row by stable key when possible and document the fallback when it disappears. Empty input clears rows while retaining columns. Keep current selection events compatible and provide a documented way to retrieve the associated record.

Use a stable, unique field for `row-key`; cost data with multiple agents per date needs a distinct record key rather than date alone. Define missing-field, duplicate-key, and `None` handling in the table design before implementation.

Put arbitrary empty-state slots in a separate follow-up: they require composition around the native table and affect its public widget API. Track that explicitly before closing the issue's core work. Native sorting exists; automatic header-click sorting is a separate interaction decision.

## Delivery Order

| Order | Deliverable | Integration and rationale |
| --- | --- | --- |
| 0 | Lifecycle and visual regression coverage | Verify repeated modal open/click/Escape behavior, visible bounds, narrow terminals, and cleanup. Add selected opt-in snapshots. Passing tests recently missed visible failures. |
| 1 | Issue #28's core runtime-table contract | Extend the existing native DataTable adapter without another runtime dependency. Directly supports usage/cost dashboards. |
| 2 | Compact styles and reusable dialogs | Opt-in TCSS preset plus confirm/prompt patterns. Explicit content/action regions let applications control sizing and alignment. |
| 3 | Shared commands and shortcuts | Add labels, shortcuts, help text, and enabled state around registered actions. Buttons, menus, and command palettes invoke the same command. |
| 4 | Targeted missing controls | Start with multiple selection and loading/empty/error presentations. Prefer native adapters; Textual already supplies SelectionList. |
| 5 | Reactive data and richer navigation | Establish table/list refresh semantics before observation. Add routing/history when an application needs more than a switcher. |
| 6 | Plotting and specialist widgets | Optional integrations driven by an actual dashboard requirement. |

Item 0 is a quality gate for subsequent additions, not a general framework rewrite. Use regression failures to justify narrowly scoped production fixes. Do not implement #28, new dialog APIs, commands, observers, or routing as part of item 0.

## Specific Patterns to Study

- [Preserved option-list highlighting](https://github.com/davep/textual-enhanced/blob/main/src/textual_enhanced/widgets/option_list.py): preserve identity across refresh. Apply the principle to tables, then runtime lists.
- [Command metadata](https://github.com/davep/textual-enhanced/blob/main/src/textual_enhanced/commands/command.py): share invocation and display metadata across interaction surfaces.
- [Confirmation dialog](https://github.com/davep/textual-enhanced/blob/main/src/textual_enhanced/dialogs/confirm.py) and [input dialog](https://github.com/davep/textual-enhanced/blob/main/src/textual_enhanced/dialogs/modal_input.py): study layout, focus, result values, and Escape behavior.
- [Textology observation and testing patterns](https://github.com/pyranha-labs/textology#top-features): useful design examples; do not import its incompatible application runtime.
- [Native SelectionList](https://textual.textualize.io/widgets/selection_list/): a substrate for multiple selection, distinct from a dropdown multi-select.
- [Textual testing](https://textual.textualize.io/guide/testing/) and [pytest-textual-snapshot](https://github.com/Textualize/pytest-textual-snapshot): use current native testing infrastructure rather than importing Textology for screenshots.

## Item 0 Acceptance Criteria

- Modal content and its action controls are visible and clickable on repeated opens, including after resize and Escape dismissal.
- Modal results, focus restoration, mounted-ID lookup, and handler cleanup behave consistently; anonymous and component-private controls do not leave retained event bindings.
- Showcase header/status bar remain visible at 120×50 and 80×24. At 60×20, content can scroll and the sidebar can be hidden; primary controls remain reachable.
- Tests assert geometry, hit targets, results, and cleanup, not exact TCSS source strings or only screen identity.
- A few deterministic SVG baselines cover the shell and reopened modal. Snapshot generation is explicitly enabled, consistent with AGENTS.md; normal pytest remains headless and does not generate screenshots.
- CI executes functional tests on Python 3.11/3.12/3.14 and snapshot comparisons in one pinned Linux/Python environment. Human inspection approves baseline changes.

## Guardrails

- Python `>=3.11,<4`; Textual `>=8.2.8,<9`; lxml `>=6.1.3,<7`.
- Core must not depend on Pillow, textual-imageview, Textology, or textual-enhanced.
- Keep strict XML and explicit linked-Python actions; no expression evaluation or embedded Python.
- Preserve unrelated root-checkout changes; implementation uses an isolated worktree.
- Do not mark a visual problem fixed from object identity, `.visible`, or green CI alone. Verify a real hit target and inspect the rendered output.
