# Testing TextUI

Follow the [checkout setup](../README.md#install-and-run), then run the normal headless suite from the repository root. All commands use Poetry's managed environment; no checkout `.venv` path is assumed:

```sh
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest -q
```

Normal tests do not create screenshots. The visual suite is collected only when `TEXTUI_VISUAL_TESTS=1` is set and compares exported Textual SVGs with reviewed baselines:

```sh
TEXTUI_VISUAL_TESTS=1 uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest tests/visual -q
```

The eight baselines per platform are stored under `tests/visual/__snapshots__/`: the showcase shell at 120×50 and 80×24, its first and reopened help modal, and unobscured Data, Activity, Controls/Choices and Controls/Details views at 80×24. View preparation uses real pointer clicks to navigate, refresh table records, select a list row, append a log entry and switch tabs. They use Textual's built-in `App.export_screenshot()` rather than an additional snapshot package because the available `pytest-textual-snapshot` release requires pytest below TextUI's supported pytest 9 range.

To intentionally update a baseline, run the commands below, then render and inspect every changed SVG before committing it. CI may regenerate SVG artifacts after a failure for inspection; it does not change committed baselines.

```sh
TEXTUI_VISUAL_TESTS=1 uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest tests/visual --snapshot-update -q
TEXTUI_VISUAL_TESTS=1 uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest tests/visual -q
```

Generate and review baselines using the same supported Python and Textual lockfile as CI. A changed SVG should correspond to a deliberate visible behavior change and include the relevant interaction test.

GitHub Actions compares the visual suite on Ubuntu 24.04 with Python 3.12. On a visual failure, it regenerates and uploads SVG artifacts for review. Reproduce the comparison locally with the same command above, using the matching platform baselines.

The separate `tests/wheel_smoke.py` runs with `python -I` in a fresh wheel-only environment outside the checkout. Its temporary linked-controller project combines reusable components, runtime-list record formatting and selection, streamed transcript updates, and a component-private tab shortcut inside a modal opened twice. CI runs this installed integration on Python 3.11, 3.12 and 3.14; it also checks that imaging dependencies remain absent.

The installed smoke also inspects built-in registry metadata and loads/builds a custom typed component with content constraints. `tests/test_registry_metadata.py` pins 52 pre-refactor validation failures, including source locations, error ordering and construction-stage diagnostics, alongside converter and custom-registration compatibility.
