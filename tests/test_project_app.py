from pathlib import Path

import pytest
from textual.widgets import Button

from textui import DocumentStateError
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
