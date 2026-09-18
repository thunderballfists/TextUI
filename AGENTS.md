# Repository Guidelines

## Project Structure

TextUI 0.2 turns strict XML into native Textual widgets. Read `README.md`, `docs/migration.md`, and `docs/superpowers/specs/2026-09-17-textui-core-design.md` before changing its public contract.

- `textui/loader.py`, `nodes.py`: strict parsing, validation, immutable definitions.
- `textui/registry.py`, `widgets/builtin_widgets.py`: explicit typed registrations and six native adapters.
- `textui/document.py`, `actions.py`: one binding per App, single-use composition, mounted lookup, explicit actions.
- `textui/styling.py`: the only adapter for Textual stylesheet internals.
- `textui/textui.py`: thin convenience App with four native message forwarders.
- `textui/errors.py`: contextual public errors.
- `examples/editor.py`, `examples/form.xml`: runnable normal-App integration and Save action.
- `tests/`: headless loader, registry, runtime, styles, action, extension, and example tests.
- `.github/workflows/tests.yml`: Python 3.11/3.12/3.14 plus build and clean-wheel verification.

## Development Commands

Run from the repository root with Python >=3.11 and Poetry 2.4.3. Keep Poetry isolated from the project, for example with `uvx --python 3.12 --from poetry==2.4.3 poetry` as the command prefix.

- `poetry install --with test`: install the locked project and test dependencies.
- `poetry run python -m pytest -q`: run all tests headlessly.
- `poetry run python -m pytest tests/test_styles.py -q`: run computed-style tests.
- `poetry run python -m examples.editor`: launch the form; Ctrl+Q quits.
- `poetry build`: create wheel and source distributions in `dist/`.
- `poetry check --lock`: validate metadata and lock consistency.

Use `poetry lock --regenerate` for intentional full dependency updates. Do not edit lock resolutions by hand. Keep environments and tools outside tracked files.

## Coding and Testing

Use four spaces, `snake_case` functions/modules, `PascalCase` classes, `UPPER_SNAKE_CASE` constants, and type annotations on new public interfaces. Match nearby code without unrelated formatting changes. No formatter or linter is configured.

Write meaningful regression tests before parsing, styling, lifecycle, or behavior changes. Name tests `test_*`; mark async tests with `@pytest.mark.asyncio`. Use Textual `run_test()` and Pilot for interactions and computed styles. Tests must not require a terminal or generate screenshots by default. Pytest uses strict asyncio mode and function-scoped event loops. The standalone `tests/wheel_smoke.py` runs with `python -I` in a fresh wheel-only environment; it is not ordinary pytest collection.

Retain the dependency boundary: importing or installing core must not pull in Pillow or textual-imageview. Documents and registrations are trusted; do not claim an untrusted-input sandbox. Custom messages require explicit forwarding; stylesheet behavior follows native Textual. Test against Python 3.11/3.12/3.14 when changing dependencies or preparing a release.

## Commits and Pull Requests

Use concise imperative summaries. PRs explain behavior changes and validation commands/results, link relevant issues, and include screenshots for visible terminal changes where helpful. Update examples and migration guidance when markup changes. Preserve unrelated local edits and use isolated worktrees when needed.
