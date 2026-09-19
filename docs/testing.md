# Testing TextUI

Run the normal headless suite from the repository root:

```sh
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest -q
```

Normal tests do not create screenshots. The visual suite is collected only when `TEXTUI_VISUAL_TESTS=1` is set and compares exported Textual SVGs with reviewed baselines:

```sh
TEXTUI_VISUAL_TESTS=1 .venv/bin/python -m pytest tests/visual -q
```

The four baselines are stored under `tests/visual/__snapshots__/`: the showcase at 120×50 and 80×24, plus its first and reopened help modal at 80×24. They use Textual's built-in `App.export_screenshot()` rather than an additional snapshot package because the available `pytest-textual-snapshot` release requires pytest below TextUI's supported pytest 9 range.

To intentionally update a baseline, run the command below, then render and inspect every changed SVG before committing it. The update command is local-only; CI never updates baselines.

```sh
TEXTUI_VISUAL_TESTS=1 .venv/bin/python -m pytest tests/visual --snapshot-update -q
TEXTUI_VISUAL_TESTS=1 .venv/bin/python -m pytest tests/visual -q
```

Generate and review baselines using the same supported Python and Textual lockfile as CI. A changed SVG should correspond to a deliberate visible behavior change and include the relevant interaction test.

GitHub Actions compares the visual suite on Ubuntu 24.04 with Python 3.12. On a visual failure, it uploads the reviewed SVG baselines so the failing run can be reproduced locally with the exact command above.
