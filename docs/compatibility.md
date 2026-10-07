# Textual Compatibility

TextUI supports Textual `>=8.2.8,<9`. The Poetry lock selects the development baseline; the installed wheel declares the supported range. These are separate checks: the full locked suite covers Python 3.11/3.12/3.14, while two Python 3.12 compatibility jobs resolve dependencies independently and run focused behavior tests against the installed wheel.

## Resolution policies

- **Lowest:** explicitly install `textual==8.2.8` alongside the wheel. The runner checks this matches the wheel's inclusive minimum. Update the CI pin deliberately if the supported floor changes.
- **Latest:** install the wheel into a fresh environment without a Textual pin. Pip selects the newest stable release satisfying its metadata and the interpreter. No Poetry lock is reused in this environment.

On 2026-10-06, [PyPI](https://pypi.org/project/textual/) lists 8.2.8 as both the minimum and newest permitted release. The jobs still exercise two resolution policies; this is not evidence for two distinct Textual versions. Later allowed releases enter the latest job automatically on the next workflow run.

Both jobs retain independent failure status, run `pip check`, log the resolved version/constraint/import origin, and reject imports outside the fresh environment. The standalone [runner](../tests/compatibility_smoke.py) reuses explicit existing regression nodes with `python -I` and pytest's importlib mode from a temporary directory. Stale node names fail collection. The usual [wheel integration](../tests/wheel_smoke.py) then verifies the combined component/modal/list/log project, authoring generation, static-check boundaries and absence of imaging dependencies.

## Reproduce locally

Apply [checkout setup](../README.md#install-and-run) in this shell and build with `uvx --python 3.12 --from poetry==2.4.3 poetry build`. Use a fresh directory for each policy; keep only the intended wheel in `dist/`. This shell example targets macOS/Linux:

```sh
repo_root="$PWD"
compat_dir="$(mktemp -d)"
uv venv --python 3.12 --seed "$compat_dir/venv"
"$compat_dir/venv/bin/python" -m pip install dist/*.whl \
  "textual==8.2.8" "pytest>=9.1.1,<10" "pytest-asyncio>=1.4.0,<2"
"$compat_dir/venv/bin/python" -m pip check
(cd "$compat_dir" && "$compat_dir/venv/bin/python" -I "$repo_root/tests/compatibility_smoke.py" lowest)
(cd "$compat_dir" && "$compat_dir/venv/bin/python" -I "$repo_root/tests/wheel_smoke.py")
```

For **latest**, create another fresh `compat_dir`, omit `"textual==8.2.8"` from installation, and pass `latest` to the runner. Running the compatibility runner in the editable Poetry environment intentionally fails its origin check. Test dependencies exist only in the compatibility environment; they do not become core dependencies.

## Internal touchpoints and regression coverage

These are review surfaces when Textual or Rich changes, not APIs that application authors should call. Leading underscores belonging to TextUI itself are not automatically upstream internals.

| Adapter | Upstream coupling | Covered behavior |
| --- | --- | --- |
| [Styling](../textui/styling.py) | Native `Stylesheet.copy/add_source/parse`, tokenizer token names, error objects and source keys; gradient renderable's `_color_gradient` | Host/document/inline cascade, block-local/theme variables, contextual errors, preset replacement and gradient geometry (`test_styles.py`, `test_bars.py`) |
| [Bars](../textui/widgets/bars.py) | `render_lines`, `Strip`, Rich grapheme/cell widths, native line filters and background colors | Gradient continuity beneath padded/aligned/wide glyphs; live cascade changes (`test_bars.py`) |
| [Tables](../textui/widgets/data_widgets.py) | `_render_cell`, `_should_highlight`, `_row_label_column_width`, `_require_update_dimensions`, `_update_count`, native component classes and event-handler chaining | Column borders, one sort per pointer click, keyboard/drag resize, frozen/scrolled geometry, refresh identity and exact native selection (`test_data_widgets.py`) |
| [Transcript](../textui/widgets/transcript.py) | RichLog `lines`, `_start_line`, `_size_known`, `_widest_line_width`, `_line_cache`; Screen selections/message signal and `TextSelected` ordering | Grapheme streaming, selection coordinates, release outside the log and invalidation after row changes (`test_log.py`) |
| [Project App](../textui/project_app.py) | `_check_resize`, `_resize_event`, debounced Screen refresh ordering; command `_bindings` | Terminal dimensions with gutters, stale resize suppression, no hooks after exit; installed command behavior (`test_project_app.py`, wheel smoke) |
| [Tab accelerators](../textui/accelerators.py) | Screen `_bindings`, native binding-chain stopping and active-screen ownership | Component-private panes remain isolated; dormant/dismissed modal shortcuts do not activate; reopen restores shortcuts (`test_accelerators.py`) |
| [Runtime list](../textui/widgets/runtime_list.py) | ListView `_nodes` index and native selection messages | Formatted labels and native record selection in the combined installed project (wheel smoke); populated-list replacement is covered by the locked `test_runtime_list.py` suite, not these installed probes |
| [Lifecycle](../textui/timers.py), [invocations](../textui/invocations.py), [modals](../textui/widgets/modal.py) | Native worker/timer state and cancellation, exact message dispatch, screen mount/unmount/focus ordering | Finished worker release, cancellation on exit, visible reopened modal click targets and explicit custom-host forwarding (`test_project_timers.py`, `test_actions.py`, `test_modal_lifecycle.py`, `test_extensions.py`) |

The runner's explicit node list defines focused coverage; the listed files contain additional regressions covered by the locked full suite. Visual baselines stay on the locked version, so a future permitted version is checked for behavior rather than byte-identical SVG output.

## Limits and upgrade procedure

This delivers the version-boundary portion of Phase 2, not complete platform compatibility. These headless probes do not verify real terminal mouse/key protocols, native clipboard tools, OSC 52 acceptance, live IDE completion or macOS/Windows CI. Optional libraries and Textual 9 are outside the declared core range.

For an intentional dependency update, review release notes and these touchpoints, regenerate the lock through the [repository workflow](../AGENTS.md), then run the full locked suite, both installed policies, visuals and clean-wheel checks. Investigate behavioral failures before changing bounds or baselines; do not silently skip probes to make a new version pass. See the [roadmap](roadmap.md#phase-2--compatibility-and-maintenance) for remaining work.
