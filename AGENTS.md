# Repository Guidelines

## Project Structure & Module Organization

TextUI is an early-stage Python library that renders HTML-like markup as Textual terminal widgets.

- `textui/textui.py`: application class, markup parsing, and widget composition.
- `textui/widgets/`: widget factory, built-in registrations, and HTML-style widgets.
- `textui/defs/`: element definitions and preprocessors for styles, dimensions, and asset paths.
- `textui/validate_css.py`: CSS validation and normalization; `textui/document.py` provides widget lookup helpers.
- `tests/`: CSS and asynchronous markup tests, plus pytest configuration.
- `examples/`: sample XML markup and image assets. `stopwatch.py` and `stopwatch.css` provide a separate Textual demo.
- `pyproject.toml` and `poetry.lock`: package metadata and dependency configuration.

## Build, Test, and Development Commands

Use Python 3.11 or a compatible version allowed by `pyproject.toml`, with Poetry. Run from the repository root unless stated otherwise:

- `poetry install --with test`: install the library and test dependencies.
- `poetry build`: create wheel and source distributions in `dist/`.
- `poetry run pytest`: run the test suite.
- `poetry run pytest tests/test_validate_css.py`: run the CSS tests alone.
- `poetry run python -c 'from textui.textui import TextUI; TextUI("examples/sample_markup.xml").run()'`: launch the sample markup application.
- `poetry run python stopwatch.py`: launch the stopwatch demo.

## Coding Style & Naming Conventions

Use four-space indentation, `snake_case` for functions and modules, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants. Follow nearby code and add type annotations to new public interfaces. Keep element registration in the factory/definition modules. No formatter or linter is configured; avoid unrelated formatting changes.

## Testing Guidelines

Use pytest and pytest-asyncio. Name files `test_*.py` and functions `test_*`; mark asynchronous tests with `@pytest.mark.asyncio`. Add assertions for changed parsing, styling, or widget behavior. No coverage threshold is configured. The current markup test forces interactive mode and writes an SVG screenshot; `--interactive` is registered but does not currently control that override.

## Commit & Pull Request Guidelines

History uses short, plain summaries such as “Include css validation and clean up.” Use concise imperative summaries; no Conventional Commits scheme is established. PRs should explain the behavior change, link relevant issues, report validation commands and results, and include screenshots for visible terminal changes. Update examples when markup behavior changes.
