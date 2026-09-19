# Shared Commands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let linked project scripts declare a command once and invoke it from a markup button or a Textual keyboard binding.

**Architecture:** Add command metadata to controller loading, while retaining the existing action dispatcher as the single callback path. A new command button resolves its presentation from that metadata at document binding time, and `ProjectApp` installs only declared command shortcuts.

**Tech Stack:** Python 3.12, Textual 8.2.8+, pytest and pytest-asyncio, Poetry 2.4.3.

**Spec:** `docs/superpowers/specs/2026-09-19-shared-commands-design.md`

## Global Constraints

- Support Python `>=3.11,<4`, Textual `>=8.2.8,<9`, and lxml `>=6.1.3,<7` without new runtime dependencies.
- Keep markup XML lowercase and kebab-case; preserve ordinary `@action` and `on-*` behavior.
- Run tests headlessly with `uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest -q`.
- Update the changelog, project-runtime documentation, and the runnable showcase for user-visible markup APIs.

## Review Focus

- A command button names an absent command: Task 2 asserts a source-located `DocumentValidationError` before composition.
- A command callback takes one argument: Task 1 asserts that linked-script loading rejects the unsupported signature.
- Two linked scripts expose the same command name: Task 1 asserts duplicate detection.
- A disabled command is activated from either its button or shortcut: Task 2 asserts neither path invokes it.
- A command without an explicit label or description: Task 1 asserts its inferred label also becomes binding help text.

### Task 1: Controller command declarations

**Files:**
- Modify: `textui/controllers.py`
- Modify: `textui/__init__.py`
- Test: `tests/test_project_app.py`

**Interfaces:**
- Produces `@command(*, label: str | None = None, shortcut: str | None = None, description: str | None = None, enabled: bool = True)`.
- Produces immutable `Command` metadata with `name`, `label`, `shortcut`, `description`, and `enabled` fields.
- Produces `ControllerSet.commands` and action wrappers for each command.

- [x] **Step 1: Write failing controller tests**

```python
@pytest.mark.asyncio
async def test_project_command_is_exposed_as_action_and_metadata(tmp_path):
    source = project(tmp_path, '<button id="plain" on-pressed="quit_app">Quit</button>', '''
from textui import command
@command(shortcut="ctrl+q")
def quit_app():
    window.app.events.append("quit")
''')
    app = ProjectApp(source)
    app.events = []
    async with app.run_test():
        assert app.controllers.commands["quit_app"].label == "Quit App"
        assert app.controllers.commands["quit_app"].description == "Quit App"
        await app.document.dispatch(Button.Pressed(app.document.get_by_id("plain")))
    assert app.events == ["quit"]

def test_command_rejects_context_parameter(tmp_path):
    source = project(tmp_path, '<label>Ready</label>', '''
from textui import command
@command()
def invalid(context): pass
''')
    with pytest.raises(DocumentValidationError, match="unsupported signature"):
        async with ProjectApp(source).run_test():
            pass

@pytest.mark.asyncio
async def test_project_rejects_duplicate_commands_from_linked_scripts(tmp_path):
    (tmp_path / "app.ui").write_text('<ui><script src="first.py"/><script src="second.py"/><label>Ready</label></ui>')
    command = 'from textui import command\n@command()\ndef close(): pass\n'
    (tmp_path / "first.py").write_text(command)
    (tmp_path / "second.py").write_text(command)
    with pytest.raises(DocumentValidationError, match="duplicate action 'close'"):
        async with ProjectApp(ProjectSource.discover(tmp_path / "app.ui")).run_test():
            pass
```

- [x] **Step 2: Run the focused tests and verify they fail because `command` is unavailable**

Run: `uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest tests/test_project_app.py -q`

Expected: failure importing `command` or missing `ControllerSet.commands`.

- [x] **Step 3: Implement the decorator and controller metadata**

```python
@dataclass(frozen=True, slots=True)
class Command:
    name: str
    label: str
    shortcut: str | None
    description: str
    enabled: bool

def command(*, label=None, shortcut=None, description=None, enabled=True):
    def decorate(function):
        function.__textui_command__ = (label, shortcut, description, enabled)
        function.__textui_action__ = True
        return function
    return decorate
```

Validate metadata and zero-argument signatures during `ControllerSet.load`, expose command callbacks through existing `actions`, and export both public symbols.

- [x] **Step 4: Run focused tests and the complete suite**

Run: `uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest tests/test_project_app.py -q && uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest -q`

Expected: all tests pass.

- [x] **Step 5: Commit the controller contract**

```bash
git add textui/controllers.py textui/__init__.py tests/test_project_app.py
git commit -m "Add project command declarations"
```

### Task 2: Command buttons and shortcuts

**Files:**
- Create: `textui/widgets/command_button.py`
- Modify: `textui/widgets/builtin_widgets.py`
- Modify: `textui/document.py`
- Modify: `textui/project_app.py`
- Test: `tests/test_project_app.py`

**Interfaces:**
- Consumes `ControllerSet.commands` and `Command` from Task 1.
- Produces `<command-button command="python_identifier" variant="..." />`.
- Produces `BoundDocument.invoke_command(name: str) -> bool`; `True` means an enabled command ran and `False` means it was disabled.

- [x] **Step 1: Write failing integration tests**

```python
@pytest.mark.asyncio
async def test_command_button_and_shortcut_invoke_the_same_command(tmp_path):
    source = project(tmp_path, '<command-button id="quit" command="quit_app"/>', '''
from textui import command
@command(label="Leave", shortcut="ctrl+q")
def quit_app(): window.app.events.append("quit")
''')
    app = ProjectApp(source)
    app.events = []
    async with app.run_test() as pilot:
        assert app.document.get_by_id("quit").label.plain == "Leave"
        await pilot.click("#quit")
        await pilot.press("ctrl+q")
        assert app.events == ["quit", "quit"]

def test_command_button_requires_a_declared_command(tmp_path):
    source = project(tmp_path, '<command-button command="missing"/>', '')
    with pytest.raises(DocumentValidationError, match="missing"):
        async with ProjectApp(source).run_test():
            pass

@pytest.mark.asyncio
async def test_disabled_command_ignores_button_and_shortcut(tmp_path):
    source = project(tmp_path, '<label id="status">Ready</label><command-button id="stop" command="stop"/>', '''
from textui import command
@command(enabled=False, shortcut="ctrl+s")
def stop(): window.document.get_by_id("status").update("Stopped")
''')
    app = ProjectApp(source)
    async with app.run_test() as pilot:
        assert app.document.get_by_id("stop").disabled
        await pilot.click("#stop")
        await pilot.press("ctrl+s")
        assert str(app.document.get_by_id("status").render()) == "Ready"
```

- [x] **Step 2: Run the focused tests and verify they fail because the tag and binding path are absent**

Run: `uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest tests/test_project_app.py -q`

Expected: parse failure for `command-button` or missing command-binding behavior.

- [x] **Step 3: Implement button lowering and shortcut dispatch**

```python
class CommandButton(Button):
    def __init__(self, command: str, *, variant: str) -> None:
        super().__init__("", variant=variant)
        self.command = command
```

Register the new typed component. Extend `Document.bind` with an optional command mapping, validate every command button, assign the metadata label and disabled state during `_build_node`, and add its `Button.Pressed` binding to the existing dispatcher. Add `BoundDocument.invoke_command`, then install each enabled-or-disabled shortcut as a first-priority Textual binding for `textui_invoke_command('name')` and await it from `action_textui_invoke_command`.

- [x] **Step 4: Run focused tests and the complete suite**

Run: `uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest tests/test_project_app.py -q && uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest -q`

Expected: all tests pass.

- [x] **Step 5: Commit the command surfaces**

```bash
git add textui/widgets/command_button.py textui/widgets/builtin_widgets.py textui/document.py textui/project_app.py tests/test_project_app.py
git commit -m "Add command buttons and shortcuts"
```

### Task 3: Showcase and user documentation

**Files:**
- Modify: `examples/showcase/app.ui`
- Modify: `examples/showcase/controller.py`
- Modify: `tests/test_showcase.py`
- Modify: `docs/project-runtime.md`
- Modify: `examples/README.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes the Task 2 command decorator, markup tag, and shortcut contract.
- Produces a showcase Quit command button and documented reusable command example.

- [x] **Step 1: Write a failing showcase interaction test**

```python
@pytest.mark.asyncio
async def test_showcase_quit_control_is_a_command_button():
    from textui import ProjectApp, ProjectSource
    entry = Path(__file__).parents[1] / "examples" / "showcase" / "app.ui"
    app = ProjectApp(ProjectSource.discover(entry))
    async with app.run_test():
        quit_button = app.document.get_by_id("quit")
        assert quit_button.label.plain == "Quit"
        assert not quit_button.disabled
```

The test must load and run the real project source, then assert the visible command control rather than inspecting XML source.

- [x] **Step 2: Run the focused test and verify it fails because the showcase still uses an ordinary button**

Run: `uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest tests/test_showcase.py -q`

Expected: failure because the existing sidebar button is not a command button or has no command metadata.

- [x] **Step 3: Convert the showcase and document the feature**

```python
@command(label="Quit", shortcut="ctrl+q", description="Exit the showcase")
def quit_app():
    window.app.exit()
```

Replace the sidebar's ordinary Quit button with `<command-button>`. Add one compact project-runtime example covering declaration, inferred labels, explicit labels, shortcut help, static disabled commands, and the boundary with `@action`. Add a changelog entry and examples index note.

- [x] **Step 4: Run showcase tests, full tests, package checks, and build**

Run: `uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest tests/test_showcase.py -q && uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest -q && uvx --python 3.12 --from poetry==2.4.3 poetry check --lock && uvx --python 3.12 --from poetry==2.4.3 poetry build`

Expected: all commands exit zero.

- [x] **Step 5: Commit documentation and example coverage**

```bash
git add examples/showcase/app.ui examples/showcase/controller.py tests/test_showcase.py docs/project-runtime.md examples/README.md CHANGELOG.md
git commit -m "Document shared commands"
```

## Final verification

- [ ] Re-read the specification and verify every public contract, validation rule, compatibility statement, and deferred boundary maps to shipped behavior.
- [ ] Run `git diff origin/main...HEAD --check` and inspect the final diff for unrelated edits.
- [ ] Run `uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest -q`, `uvx --python 3.12 --from poetry==2.4.3 poetry check --lock`, and `uvx --python 3.12 --from poetry==2.4.3 poetry build`.
