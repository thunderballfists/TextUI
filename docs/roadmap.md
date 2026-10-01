# TextUI Roadmap

Updated: 2026-09-30. Status: Phase 0 complete; Phase 1 planned. Initial review baseline: `f8e472c` (TextUI 0.6.0).

This is the current delivery order. The [extension triage](2026-09-19-extension-triage.md) retains the historical library comparisons and adoption rationale. Its external compatibility claims are dated evidence and must be checked again before adding a dependency.

## Direction

Keep the HTML-like authoring model: strict XML describes structure, native TCSS describes appearance, and linked Python supplies behavior. Preserve explicit registry extensions, normal Textual App integration, contextual errors, and the image-free core dependency boundary.

Prioritize reliable application lifecycles and approachable authoring before expanding the widget catalog. Each phase has a completion gate; the numbers express dependencies, not calendar promises.

## Current baseline

Main includes reusable local components and slots; linked scripts, includes and styles; actions, commands and timers; context and resize hooks; navigation, splits and modals; runtime tables/lists; compact/border presets; gradients; native range controls; autofocus on reveal; selectable logs and asynchronous clipboard copying.

The initial review ran 389 committed headless tests successfully, but separate behavioral probes exposed five defects. All five are fixed in [PR #93](https://github.com/thunderballfists/TextUI/pull/93), merged at `9e5a464`. The resulting suite has 431 passing tests, including 34 cases that reproduced defects before their fixes and one additional ordering compatibility case.

## Phase 0 — Reliability (completed)

| Unit | Deliverable | Completion gate |
| --- | --- | --- |
| 0A | Shared action/command ownership and lifecycle cleanup | Untargeted tasks are cancelled on close; sync completion/failure cleans target state; loading remains while any action owns the target; supersession cannot publish stale target state. |
| 0B | Timer worker cleanup | Completed async/threaded workers are released; repeated close stops timers and clears ownership; overlap skipping and native error reporting remain intact. |
| 0C | Exact table sorting | Adjacent large integers and arbitrarily large integers sort correctly; mixed numeric/text values, missing values, NaN and infinity have documented deterministic behavior; refresh retains sort and row identity. |

Delivered 0A, 0B and 0C as separate logical commits in one reviewed reliability PR. All completion gates above are met. Independent review found no actionable issues; the Python 3.11/3.12/3.14 test, build and clean-wheel matrix, lint and Linux visual checks passed. Local visual comparison passed all six checks without baseline changes. GitHub feedback was checked before and after merge; no comments or unresolved threads were present.

Next: 1A, dependable setup and showcase launch. Phase 1B's trusted-controller validation boundary still needs its own design before implementation.

Detailed artifacts: [reliability design](superpowers/specs/2026-09-30-runtime-reliability-design.md) and [implementation plan](superpowers/plans/2026-09-30-runtime-reliability.md).

## Phase 1 — Developer experience

| Unit | Scope | Completion gate |
| --- | --- | --- |
| 1A | Dependable setup and showcase launch | Document one isolated environment path and a module-based launch; verify from a clean checkout and another working directory. A small launcher may wrap the existing Poetry workflow. |
| 1B | Project validation and CLI diagnostics | Add a headless `textui check` workflow, concise expected-error output and stable exit codes; missing files, XML, TCSS and action errors retain their source location. Keep tracebacks available for unexpected failures/debugging. |
| 1C | Registry-derived authoring reference | Generate tags, attributes, defaults, events and examples from registry metadata; provide machine-readable completion data. Compound structural rules remain explicit, and custom components remain supported. |
| 1D | Documentation consolidation | Separate current reference from historical design records; reconcile migration/examples/testing guidance and shipped roadmap items; make install, launch and extension paths easy to find. |

1A and 1D can proceed alongside Phase 0. Design 1B's execution boundary first: full validation may need trusted controller setup to register components. The command must explain which hooks execute and must not claim static or sandboxed validation. 1C depends on that boundary and on an explicit metadata format; a complete XML schema is a later step if it can express compound rules accurately.

## Phase 2 — Compatibility and maintenance

- Run focused behavioral probes against the lowest and latest allowed Textual versions, supplementing the locked full suite and existing clean-wheel smoke test. Cover styling, gradients, table rendering/resizing, selection, resize hooks, modals and shutdown.
- Add focused macOS/Windows CI for platform-specific code. Keep mocked clipboard tests; exercise real native tools only in disposable CI environments. Terminal OSC 52 acceptance remains a separate manual check.
- Expand clean-wheel checks to newer runtime facilities and verify that optional imaging packages remain absent.
- Share built-in message forwarding between convenience Apps while preserving exact-type dispatch and explicit custom-event forwarding in normal hosts.
- Improve public typing and editor support for the injected `window`; introduce type checks incrementally around supported public interfaces.

Gate: reviewed compatibility coverage, clean installed-wheel checks, documented Textual internal touchpoints, and no regression in host extension behavior. Preserve the Poetry lock policy; do not hand-edit dependency resolutions.

## Phase 3 — Focused application capabilities

| Order | Capability | Boundary and acceptance |
| --- | --- | --- |
| 3A | `<sparkline>` | Small native adapter with validated numeric data and a controller update API; include a live showcase trend and empty-data coverage. |
| 3B | `<selection-list>` | Explicit selected values, stable item identity, disabled choices, runtime replacement and one selection-changed event; keyboard and pointer tests. |
| 3C | Command palette | Reuse existing command metadata and invocation ownership; searchable labels/descriptions, keyboard access and correct disabled-command behavior. |
| 3D | Loading, empty and error presentation | Reusable component patterns built on proven target lifecycle semantics; include retry examples without automatic network/retry policy. |

Each capability gets a small design and implementation plan before code. Define its runtime update and event semantics, not just its markup spelling. Keep the showcase and reference synchronized with each addition.

## Phase 4 — Extensions and richer authoring

- Optional plotting: axes, legends and multiple series in a separate adapter/package after sparkline establishes the basic dashboard contract.
- Optional images: revisit the preferred renderer's compatibility and license before a separate image distribution; retain Python 3.11 and the image-free core.
- Date picking and autocomplete/combobox: decide ISO value, provider, identity and refresh behavior before adopting a library.
- Component-local styling and explicit state updates: design scope, cascade, ownership and instance isolation against a real application example.
- Routing/history and dynamic component properties: pursue when a concrete application exceeds the current content-switcher and controller APIs.

Embedded Python, expression evaluation, automatic data binding, hot reload/recomposition, terminal emulation and an untrusted-document mode remain separate architectural work, with no delivery commitment here.

## Delivery rules

Use an isolated worktree for implementation and preserve root-checkout edits. Write symptom-driven regressions before fixes. Update user-facing docs/examples and `CHANGELOG.md` when behavior changes. Run focused checks, the full committed suite, relevant visual checks, Pyflakes, lock validation and builds; use Python 3.11/3.12/3.14 for releases/dependency changes. Obtain independent review, inspect GitHub feedback and resolve verified findings before merging. Read the historical review threads again after merge if feedback arrives late.

Move a unit to completed only when its gate is met. Record the merged PR and validation evidence here; unchecked historical plan lists do not override this current status.
