# Changelog

All notable changes to TextUI are documented here.

## [Unreleased]

### Fixed

- Modal dismissal now releases anonymous and component-private action bindings, and failed modal pushes roll back their registrations.
- Duplicate opens of one declared modal now raise `DocumentStateError` instead of leaking state or surfacing a native duplicate-ID error.
- Modal result futures now resolve after their screen unmounts, allowing immediate reopen of the same declaration.

### Changed

- Compound-control validation now rejects unreachable nested radio-button events while preserving custom registry components that reuse built-in tag names.

### Added

- Project-local reusable `.ui` components with explicit imports, literal string properties, named slots, fallback content, and per-instance private template IDs.
- A runnable feature showcase that combines every built-in widget family and project-runtime facility.
- Runtime data-table rows through `row-key`, typed column `label`/`align`/`width` metadata, atomic `set_rows()`, and read-only `get_record()`.
- Clickable data-table headings that toggle ascending and descending order, using original runtime record values or displayed seed values.

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
