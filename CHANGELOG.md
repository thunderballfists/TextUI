# Changelog

All notable changes to TextUI are documented here.

## [Unreleased]

### Fixed

- Streaming a single transcript line no longer rescans everything already
  accumulated on each delta: `TranscriptLog` tracks the active line's width and
  printability incrementally, so per-delta work is proportional to the delta.
- Streamed transcript deltas that land mid grapheme cluster now fall back to the
  rewrite path, so combining marks, variation selectors, joiners, skin-tone
  modifiers, matras, and jamo are no longer dropped from a streamed line.
- Project-owned timers now also stand down once the message pump stops, closing
  the teardown window in which a tick could reach an already-unmounted document.
- Async commands now apply declared target lifecycle state when invoked from command controls and shortcuts.
- Command shortcuts now schedule async work without blocking later input, and lifecycle targets retain every concurrent task through completion or shutdown.
- Command shortcuts now reject invalid keys, duplicate declarations, and conflicts with tab accelerators.
- Project-owned timers stop as soon as application exit begins, preventing teardown callbacks from touching disposed widgets.
- Projects that exit during `on_ready` no longer try to start periodic timers during teardown.
- Async action failures now preserve immediate dispatch errors and report delayed failures with their markup source location.
- Modal state and action bindings are released when an application shuts down with a modal open.
- Concurrent runtime-list replacements are serialized so stale rows cannot remain mounted.
- Transcript streaming retains text finalized before initial layout and falls back to Rich rendering for control characters.
- Modal dismissal now releases anonymous and component-private action bindings, and failed modal pushes roll back their registrations.
- Duplicate opens of one declared modal now raise `DocumentStateError` instead of leaking state or surfacing a native duplicate-ID error.
- Modal result futures now resolve after their screen unmounts, allowing immediate reopen of the same declaration.

### Changed

- Splits now consume the remaining height in structural application shells, leaving header and status-bar space without custom height rules.
- Compound-control validation now rejects unreachable nested radio-button events while preserving custom registry components that reuse built-in tag names.
- Runtime-list `item-label` patterns now require every replacement field to be a direct mapping key, including nested format specifications.

### Added

- Linear-gradient backgrounds for `header` and `status-bar` surfaces, declared with an ID selector in TCSS and rendered beneath native bar controls.
- `autofocus="true"` for focusable controls, including component instances, newly opened modal controls, and controls in tabs when their pane activates, with default accent focus outlines.
- Modal dismissal results now expose a `.mounted` awaitable for safely populating widgets after a modal opens.
- Runtime data tables without `row-key` now use stable positional keys for each replacement batch; declared duplicate keys report their table and markup source.
- Opt-in data-table striping, vertical column borders, and keyboard or drag resizing, with headers and seeded cells honoring each column's alignment.
- Native integer `<range>` controls with keyboard and pointer interaction, controller-settable values, changed events, and TCSS component classes.
- Optional `target` and `supersede` lifecycle metadata for async actions and commands, including target loading/error state and shutdown cancellation.
- Opt-in `<style preset="compact"/>` TCSS for dense native controls, including native borderless vertical compaction, normal project stylesheet override order, and runtime switching through `window.document.toggle_style_preset()`.
- Opt-in `<style preset="borders"/>` TCSS for rounded and double Unicode button outlines, independently switchable at runtime.
- `<log>` transcripts with bounded history, Rich complete entries, literal streamed deltas, and scroll-following state.
- Shared project commands through `@command`, self-labeling `<command-button>` markup, static enabled state, and shortcut help.
- Project-local reusable `.ui` components with explicit imports, literal string properties, named slots, fallback content, and per-instance private template IDs.
- A runnable feature showcase that combines every built-in widget family and project-runtime facility.
- Runtime data-table rows through `row-key`, typed column `label`/`align`/`width` metadata, atomic `set_rows()`, and read-only `get_record()`.
- Clickable data-table headings with independent hover states, a full-cell active `↑`/`↓` background, and sorting by original runtime record values or displayed seed values.
- Runtime table refreshes retain an active column sort instead of reverting to source order.

### Planned

- Optional image components remain outside the core package.
- Future releases may add capabilities without changing the strict document and lifecycle contracts established in 0.2.

## [0.6.0] - 2026-09-18

### Added

- Native data-table and tree markup with declarative seed rows, columns, cells, and nested nodes.
- Row, cell, and node selection actions, structural validation, and a runnable data example.

## [0.5.0] - 2026-09-18

### Added

- Native radio-set/radio-button, collapsible, progress-bar, and rule markup with typed attributes and explicit events.
- Compound radio validation and an expanded controls example.

## [0.4.0] - 2026-09-18

### Added

- Native select/option, switch, text-area, and tabbed-content/tab-pane markup with explicit events.
- Verbatim text-area content, compound-control validation, and a runnable controls example.

## [0.3.0] - 2026-09-18

### Added

- A local `.ui` project runtime with `textui run`, nested markup includes, sourced TCSS, and linked Python controllers.
- App-scoped `window`, explicit `@action` exports, setup/ready/close hooks, and Textual-backed one-shot and periodic timers.
- A runnable project example and authoring guide.
- Two-pane draggable and hideable layouts, navigation selection, and native content switching.

## [0.2.1] - 2026-09-18

- Expanded the examples with a documented static six-widget sample and regression coverage for loading it.
- Clarified the README, migration guide, and contributor workflow.

## [0.2.0] - 2026-09-18

TextUI 0.2 is a breaking pre-1.0 reboot of the experimental 0.1 API.

### Added

- Strict UTF-8 XML loading through `DocumentLoader.from_string` and `from_file`.
- Immutable document, node, registry, attribute, and event definitions.
- Six native components: `vertical`, `horizontal`, `label`, `button`, `input`, and `checkbox`.
- Explicit typed component registration and converter helpers for booleans, integers, and enums.
- Native Textual bindings with single-use composition, mounted ID lookup, and independent bindings per App.
- Explicit synchronous and asynchronous Python actions with contextual `ActionContext` errors.
- Native TCSS blocks, literal inline styles, stylesheet staging, cascade tests, and custom component/message forwarding.
- Runnable editor example, migration guide, Python 3.11/3.12/3.14 CI, and clean-wheel smoke checks.

### Changed

- Markup now requires one attribute-free `<ui>` root and lowercase kebab-case names.
- Leaf text is literal and no longer interpreted as Rich/Textual markup.
- Styling delegates validation and cascade behavior to Textual.
- Package dependencies are bounded to Python `>=3.11,<4`, Textual `>=8.2.8,<9`, and lxml `>=6.1.3,<7`.

### Removed

- Embedded scripts, expression evaluation, browser-style DOM helpers, HTML aliases, custom CSS filtering, and core image widgets.
- Mandatory Pillow and `textual-imageview` dependencies.

[Unreleased]: https://github.com/thunderballfists/TextUI/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/thunderballfists/TextUI/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/thunderballfists/TextUI/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/thunderballfists/TextUI/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/thunderballfists/TextUI/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/thunderballfists/TextUI/releases/tag/v0.2.1
[0.2.0]: https://github.com/thunderballfists/TextUI/releases/tag/v0.2.0
