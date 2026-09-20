import asyncio
from pathlib import Path

import pytest
from textual.widgets import Button

from textui import DocumentStateError, DocumentValidationError
from textui.project import ProjectSource
from textui.project_app import ProjectApp


def project(tmp_path: Path, markup: str, script: str) -> ProjectSource:
    (tmp_path / "app.ui").write_text(
        f'<ui><script src="controller.py"/>{markup}</ui>', encoding="utf-8"
    )
    (tmp_path / "controller.py").write_text(script, encoding="utf-8")
    return ProjectSource.discover(tmp_path / "app.ui")


@pytest.mark.asyncio
async def test_project_setup_registers_component_before_lowering_and_ready_can_look_up_widget(tmp_path: Path):
    source = project(tmp_path, '<status id="status"/>', '''
from textui import ComponentSpec
from textual.widgets import Label

def on_setup():
    window.app.events.append("setup")
    window.registry.register(ComponentSpec("status", lambda context: Label("Ready")))

async def on_ready():
    window.app.events.append(window.document.get_by_id("status").id)

def on_close():
    window.app.events.append("close")
''')
    app = ProjectApp(source)
    app.events = []
    with pytest.raises(DocumentStateError):
        _ = app.window.document

    async with app.run_test():
        assert app.events == ["setup", "status"]
    assert app.events == ["setup", "status", "close"]


@pytest.mark.asyncio
async def test_actions_are_explicit_and_module_state_is_per_app(tmp_path: Path):
    source = project(tmp_path, '<button id="go" on-pressed="increment">Go</button>', '''
from textui import action
count = 0

@action
def increment():
    global count
    count += 1
    window.app.events.append(count)

def hidden():
    raise AssertionError("not exported")
''')
    first, second = ProjectApp(source), ProjectApp(source)
    first.events, second.events = [], []
    async with first.run_test():
        button = first.document.get_by_id("go")
        await first.document.dispatch(Button.Pressed(button))
        await first.document.dispatch(Button.Pressed(button))
    async with second.run_test():
        button = second.document.get_by_id("go")
        await second.document.dispatch(Button.Pressed(button))
    assert first.events == [1, 2]
    assert second.events == [1]
    assert first.window is not second.window


@pytest.mark.asyncio
async def test_project_command_is_exposed_as_action_and_metadata(tmp_path: Path):
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


@pytest.mark.asyncio
async def test_project_action_lifecycle_metadata_targets_a_declared_id(tmp_path: Path):
    source = project(tmp_path, '<label id="status">Ready</label>', '''
from textui import action

@action(target="status", supersede=True)
async def refresh(context):
    window.app.target = context.target
    window.app.cancelled = context.cancelled
''')
    app = ProjectApp(source)

    async with app.run_test():
        metadata = app.document.action_metadata["refresh"]
        assert metadata.target == "status"
        assert metadata.supersede is True


@pytest.mark.asyncio
async def test_project_rejects_action_lifecycle_unknown_target(tmp_path: Path):
    source = project(tmp_path, '<label id="status">Ready</label>', '''
from textui import action

@action(target="missing")
def refresh():
    pass
''')

    with pytest.raises(DocumentValidationError, match="target"):
        async with ProjectApp(source).run_test():
            pass


@pytest.mark.asyncio
async def test_command_rejects_context_parameter(tmp_path: Path):
    source = project(tmp_path, '<label>Ready</label>', '''
from textui import command

@command()
def invalid(context):
    pass
''')

    with pytest.raises(DocumentValidationError, match="unsupported signature"):
        async with ProjectApp(source).run_test():
            pass


@pytest.mark.asyncio
async def test_project_rejects_duplicate_commands_from_linked_scripts(tmp_path: Path):
    (tmp_path / "app.ui").write_text(
        '<ui><script src="first.py"/><script src="second.py"/><label>Ready</label></ui>',
        encoding="utf-8",
    )
    command_source = 'from textui import command\n\n@command()\ndef close():\n    pass\n'
    (tmp_path / "first.py").write_text(command_source, encoding="utf-8")
    (tmp_path / "second.py").write_text(command_source, encoding="utf-8")
    app = ProjectApp(ProjectSource.discover(tmp_path / "app.ui"))

    with pytest.raises(DocumentValidationError, match="duplicate action 'close'"):
        async with app.run_test():
            pass


@pytest.mark.asyncio
async def test_command_button_and_shortcut_invoke_the_same_command(tmp_path: Path):
    source = project(tmp_path, '<command-button id="quit" command="quit_app"/>', '''
from textui import command

@command(label="Leave", shortcut="ctrl+q")
def quit_app():
    window.app.events.append("quit")
''')
    app = ProjectApp(source)
    app.events = []

    async with app.run_test() as pilot:
        assert app.document.get_by_id("quit").label.plain == "Leave"
        await pilot.click("#quit")
        await pilot.press("ctrl+q")

    assert app.events == ["quit", "quit"]


@pytest.mark.asyncio
async def test_command_target_lifecycle_tracks_async_command(tmp_path: Path):
    source = project(tmp_path, '<command-button id="refresh" command="refresh"/><label id="status">Ready</label>', '''
import asyncio
from textui import command

@command(target="status")
async def refresh():
    window.app.started.set()
    await window.app.release.wait()
''')
    app = ProjectApp(source)
    app.started = asyncio.Event()
    app.release = asyncio.Event()

    async with app.run_test() as pilot:
        task = asyncio.create_task(app.document.invoke_command("refresh"))
        await app.started.wait()
        assert app.document.get_by_id("status").has_class("-loading")
        app.release.set()
        assert await task is True
        await pilot.pause()
        assert not app.document.get_by_id("status").has_class("-loading")


@pytest.mark.asyncio
async def test_command_target_lifecycle_can_supersede_previous_invocation(tmp_path: Path):
    source = project(tmp_path, '<label id="status">Ready</label>', '''
import asyncio
from textui import command

@command(target="status", supersede=True)
async def refresh():
    window.app.calls += 1
    if window.app.calls == 2:
        window.app.second_started.set()
    await window.app.release.wait()
''')
    app = ProjectApp(source)
    app.calls = 0
    app.release = asyncio.Event()
    app.second_started = asyncio.Event()

    async with app.run_test() as pilot:
        first = asyncio.create_task(app.document.invoke_command("refresh"))
        await pilot.pause()
        second = asyncio.create_task(app.document.invoke_command("refresh"))
        await app.second_started.wait()
        with pytest.raises(asyncio.CancelledError):
            await first
        assert app.document.get_by_id("status").has_class("-loading")
        app.release.set()
        assert await second is True
        await pilot.pause()
        assert not app.document.get_by_id("status").has_class("-loading")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("declared_shortcut", "canonical_shortcut"),
    [("+", "plus"), ("plus", "plus"), ("!", "exclamation_mark"), ("exclamation_mark", "exclamation_mark")],
)
async def test_command_printable_shortcuts_normalize_and_invoke(tmp_path: Path, declared_shortcut: str, canonical_shortcut: str):
    source = project(tmp_path, '<label>Ready</label>', f'''
from textui import command

@command(shortcut={declared_shortcut!r})
def run():
    window.app.events.append("run")
''')
    app = ProjectApp(source)
    app.events = []

    async with app.run_test() as pilot:
        assert app.controllers.commands["run"].shortcut == canonical_shortcut
        await pilot.press(canonical_shortcut)

    assert app.events == ["run"]


@pytest.mark.asyncio
@pytest.mark.parametrize("shortcut", ["not a real key!!", "ctrl+unknown", "ctrl+q,ctrl+w"])
async def test_command_rejects_invalid_shortcuts(tmp_path: Path, shortcut: str):
    source = project(tmp_path, '<label>Ready</label>', f'''
from textui import command

@command(shortcut={shortcut!r})
def invalid():
    pass
''')

    with pytest.raises(DocumentValidationError, match="command shortcut"):
        async with ProjectApp(source).run_test():
            pass


@pytest.mark.asyncio
async def test_project_rejects_duplicate_command_shortcuts(tmp_path: Path):
    source = project(tmp_path, '<label>Ready</label>', '''
from textui import command

@command(shortcut="ctrl+k")
def first():
    pass

@command(shortcut="ctrl+k")
def second():
    pass
''')

    with pytest.raises(DocumentValidationError, match="duplicate command shortcut 'ctrl\\+k'"):
        async with ProjectApp(source).run_test():
            pass


@pytest.mark.asyncio
async def test_project_rejects_command_shortcut_that_shadows_tab_accelerator(tmp_path: Path):
    source = project(tmp_path, '''
<tabbed-content><tab-pane id="one" title="One" accelerator="1" accelerator-scope="document"><label>One</label></tab-pane></tabbed-content>
''', '''
from textui import command

@command(shortcut="1")
def first():
    pass
''')

    with pytest.raises(DocumentValidationError, match="conflicts with tab accelerator '1'"):
        async with ProjectApp(source).run_test():
            pass


@pytest.mark.asyncio
async def test_command_button_requires_a_declared_command(tmp_path: Path):
    source = project(tmp_path, '<command-button command="missing"/>', '')

    with pytest.raises(DocumentValidationError, match="missing"):
        async with ProjectApp(source).run_test():
            pass


@pytest.mark.asyncio
async def test_disabled_command_ignores_button_and_shortcut(tmp_path: Path):
    source = project(tmp_path, '<label id="status">Ready</label><command-button id="stop" command="stop"/>', '''
from textui import command

@command(enabled=False, shortcut="ctrl+s")
def stop():
    window.document.get_by_id("status").update("Stopped")
''')
    app = ProjectApp(source)

    async with app.run_test() as pilot:
        assert app.document.get_by_id("stop").disabled
        await pilot.click("#stop")
        await pilot.press("ctrl+s")
        assert str(app.document.get_by_id("status").render()) == "Ready"


@pytest.mark.asyncio
async def test_disabled_command_ignores_direct_event_binding(tmp_path: Path):
    source = project(tmp_path, '<button id="stop" on-pressed="stop">Stop</button>', '''
from textui import command

@command(enabled=False)
def stop():
    window.app.events.append("ran")
''')
    app = ProjectApp(source)
    app.events = []

    async with app.run_test() as pilot:
        assert await pilot.click("#stop")
        await pilot.pause()
    assert app.events == []


@pytest.mark.asyncio
async def test_host_and_linked_action_name_collision_fails_before_mount(tmp_path: Path):
    source = project(tmp_path, '<button on-pressed="save">Save</button>', '''
from textui import action
@action
def save():
    pass
''')
    app = ProjectApp(source, actions={"save": lambda context: None})

    with pytest.raises(Exception, match="duplicate.*save"):
        async with app.run_test():
            pass


@pytest.mark.asyncio
async def test_setup_failure_still_calls_close_with_source_context(tmp_path: Path):
    source = project(tmp_path, '', '''
def on_setup():
    window.app.events.append("setup")
    raise ValueError("broken")

def on_close():
    window.app.events.append("close")
''')
    app = ProjectApp(source)
    app.events = []

    with pytest.raises(Exception, match="on_setup.*broken"):
        async with app.run_test():
            pass
    assert app.events == ["setup", "close"]


@pytest.mark.asyncio
async def test_ready_failure_calls_close_once(tmp_path: Path):
    source = project(tmp_path, '<label id="ready">Ready</label>', '''
def on_setup():
    window.app.events.append("setup")

def on_ready():
    window.app.events.append(window.document.get_by_id("ready").id)
    raise ValueError("ready broke")

def on_close():
    window.app.events.append("close")
''')
    app = ProjectApp(source)
    app.events = []
    with pytest.raises(Exception, match="on_ready.*ready broke"):
        async with app.run_test():
            pass
    assert app.events == ["setup", "ready", "close"]


@pytest.mark.asyncio
async def test_scripts_execute_in_entry_order_once_per_app(tmp_path: Path):
    (tmp_path / "app.ui").write_text(
        '<ui><script src="first.py"/><script src="second.py"/><label>Hi</label></ui>', encoding="utf-8"
    )
    (tmp_path / "first.py").write_text('window.app.events.append("first")', encoding="utf-8")
    (tmp_path / "second.py").write_text('window.app.events.append("second")', encoding="utf-8")
    app = ProjectApp(ProjectSource.discover(tmp_path / "app.ui"))
    app.events = []
    async with app.run_test():
        assert app.events == ["first", "second"]


@pytest.mark.asyncio
async def test_close_hook_error_propagates_with_script_source(tmp_path: Path):
    source = project(tmp_path, '<label>Hi</label>', '''
def on_close():
    raise ValueError("close broke")
''')
    app = ProjectApp(source)
    with pytest.raises(Exception, match="on_close.*close broke") as caught:
        async with app.run_test():
            pass
    assert "controller.py" in str(caught.value)
