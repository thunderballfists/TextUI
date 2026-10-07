# Testing TextUI

Follow the [checkout setup](../README.md#install-and-run), then run the normal headless suite from the repository root. All commands use Poetry's managed environment; no checkout `.venv` path is assumed:

```sh
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest -q
```

Normal tests do not create screenshots. The visual suite is collected only when `TEXTUI_VISUAL_TESTS=1` is set and compares exported Textual SVGs with reviewed baselines:

```sh
TEXTUI_VISUAL_TESTS=1 uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest tests/visual -q
```

The visual suite has ten tests: two helper checks and eight screenshot comparisons. The eight baselines per platform are stored under `tests/visual/__snapshots__/`: the showcase shell at 120×50 and 80×24, its first and reopened help modal, and unobscured Data, Activity, Controls/Choices and Controls/Details views at 80×24. View preparation uses real pointer clicks to navigate, refresh table records, select a list row, append a log entry and switch tabs. They use Textual's built-in `App.export_screenshot()` rather than an additional snapshot package because the available `pytest-textual-snapshot` release requires pytest below TextUI's supported pytest 9 range.

To intentionally update a baseline, run the commands below, then render and inspect every changed SVG before committing it. CI may regenerate SVG artifacts after a failure for inspection; it does not change committed baselines.

```sh
TEXTUI_VISUAL_TESTS=1 uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest tests/visual --snapshot-update -q
TEXTUI_VISUAL_TESTS=1 uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest tests/visual -q
```

Generate and review baselines using the same supported Python and Textual lockfile as CI. A changed SVG should correspond to a deliberate visible behavior change and include the relevant interaction test.

GitHub Actions compares the visual suite on Ubuntu 24.04 with Python 3.12. On a visual failure, it regenerates and uploads SVG artifacts for review. Reproduce the comparison locally with the same command above, using the matching platform baselines.

The separate `tests/wheel_smoke.py` runs with `python -I` in a fresh wheel-only environment outside the checkout. Its temporary linked-controller project combines reusable components, runtime-list record formatting and selection, streamed transcript updates, and a component-private tab shortcut inside a modal opened twice. CI runs this installed integration on Python 3.11, 3.12 and 3.14; it also checks that imaging dependencies remain absent.

The installed smoke also inspects built-in registry metadata and loads/builds a custom typed component with content constraints. `tests/test_registry_metadata.py` pins 52 pre-refactor validation failures, including source locations, error ordering and construction-stage diagnostics, alongside converter and custom-registration compatibility.

## Authoring and example checks

The following tools are unreleased on `main`; run them after installing the current checkout. Validate an entry without importing its controller, then use trusted checking for callable bindings, native construction and TCSS:

```sh
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m textui check --static --format json examples/showcase/app.ui
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m textui check examples/showcase/app.ui
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest tests/test_authoring.py tests/test_authoring_schema.py tests/test_static_check.py -q
```

The authoring tests compare all seven committed artifacts with registry-derived output, compile both schemas, check structural exceptions, and validate example/README markup. Raw component/include projects require the permissive profile plus static checking; strict XSD validates built-in-only or expanded markup. Python-registered tags require their trusted registry. Generation and static success do not establish native styling, mounted behavior or manual IDE completion; see [editor verification](editors.md#maintainer-verification).

After intentionally changing registry metadata, authoring facts, canonical samples or the package version, reinstall the project and regenerate:

```sh
uvx --python 3.12 --from poetry==2.4.3 poetry install --with test --no-interaction
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m textui spec --output .
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest tests/test_authoring.py tests/test_authoring_schema.py -q
```

Review the generated diff; do not hand-edit artifacts. Canonical markup samples under `textui/authoring/samples/` must match their corresponding example sources. The installed generator uses bundled samples, not checkout-relative paths.

## Build and installed-wheel verification

Use these checks before packaging changes or a release:

```sh
uvx --python 3.12 --from poetry==2.4.3 poetry check --lock
uvx --python 3.12 --from poetry==2.4.3 poetry build
uvx --python 3.12 --from pyflakes python -m pyflakes textui
```

From the repository root, build first, then reproduce the wheel boundary in a disposable directory:

```sh
repo_root="$PWD"
wheel_check_dir="$(mktemp -d)"
uv venv --python 3.12 "$wheel_check_dir/venv"
uv pip install --python "$wheel_check_dir/venv/bin/python" dist/*.whl
uv pip check --python "$wheel_check_dir/venv/bin/python"
(cd "$wheel_check_dir" && "$wheel_check_dir/venv/bin/python" -I "$repo_root/tests/wheel_smoke.py")
```

This shell example targets macOS/Linux; CI repeats it with each matrix interpreter. Keep only the intended wheel in `dist/` when using the glob. The smoke test also generates all authoring artifacts and verifies static checking cannot execute its sentinel controller. The source archive includes runnable examples, documentation, schemas, lockfile and launcher; the wheel includes the library and generator's canonical samples, not a runnable `examples` package.

## Textual compatibility policies

The reusable test workflow also builds fresh Python 3.12 environments for Textual's **lowest** and **latest allowed** resolution. These run `tests/compatibility_smoke.py` outside the checkout with isolated imports, then the full installed-wheel smoke. They supplement the locked full suite and visuals; they do not change the Poetry lock. See the [compatibility guide](compatibility.md) for reproducible commands, the internal-touchpoint map and explicit platform limits.
