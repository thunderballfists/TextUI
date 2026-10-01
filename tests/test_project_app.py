import asyncio
from pathlib import Path

import pytest
from textual.events import Resize
from textual.geometry import Size
from textual.widgets import Button

from textui import DocumentStateError, DocumentValidationError
from textui.errors import ActionExecutionError
from textui.project import ProjectSource
from textui.project_app import ProjectApp


def project(tmp_path: Path, markup: str, script: str) -> ProjectSource:
    (tmp_path / "app.ui").write_text(
        f'<ui><script src="controller.py"/>{markup}</ui>', encoding="utf-8"
    )
    (tmp_path / "controller.py").write_text(script, encoding="utf-8")
    return ProjectSource.discover(tmp_path / "app.ui")


@pytest.mark.asyncio
@pytest.mark.parametrize("entry", ["command", "event"])
@pytest.mark.parametrize("fails", [False, True])
async def test_sync_target_command_finishes_state_and_preserves_error_source(tmp_path, entry, fails):
    source = project(tmp_path, '<button id="button" on-pressed="refresh"/><label id="status"/>', '''
from textui import command
@command(target="status")
def refresh():
    window.app.was_loading = window.document.get_by_id("status").has_class("-loading")
    if window.app.fails:
        raise window.app.original_error
''')
    app = ProjectApp(source)
    app.fails = fails
    app.original_error = ValueError("refresh failed")
    async with app.run_test():
        status = app.document.get_by_id("status")
        status.add_class("-error")
        status.textui_error = "old error"
        invoke = app.document.invoke_command("refresh") if entry == "command" else app.document.dispatch(
            Button.Pressed(app.document.get_by_id("button")))
        if fails:
            with pytest.raises(ActionExecutionError) as caught:
                await invoke
            assert caught.value.__cause__ is app.original_error
            expected_source = "controller.py" if entry == "command" else "app.ui"
            assert caught.value.location.source.endswith(expected_source)
            assert status.has_class("-error")
            assert status.textui_error == "refresh failed"
        else:
            assert await invoke
            assert not status.has_class("-error")
            assert status.textui_error is None
        assert app.was_loading
        assert not status.has_class("-loading")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["action", "command"])
async def test_project_shutdown_cancels_untargeted_action_and_command(tmp_path, kind):
    signature = "context" if kind == "action" else ""
    source = project(tmp_path, '<button id="button" on-pressed="wait"/>', f'''
import asyncio
from textui import {kind}
@{kind}()
async def wait({signature}):
    window.app.started.set()
    try:
        await window.app.release.wait()
        window.app.effects.append(window.phase)
    except asyncio.CancelledError:
        window.app.cancelled.set()
        raise
    finally:
        window.app.finished.set()
''')
    app = ProjectApp(source)
    app.started, app.release, app.cancelled, app.finished = (asyncio.Event() for _ in range(4))
    app.effects = []
    try:
        async with app.run_test():
            if kind == "action":
                await app.document.dispatch(Button.Pressed(app.document.get_by_id("button")))
            else:
                app.document.start_command("wait")
            await app.started.wait()
        assert app.window.phase == "closed"
        assert app.cancelled.is_set()
        app.release.set()
        await asyncio.wait_for(app.finished.wait(), timeout=1)
        assert app.effects == []
    finally:
        app.release.set()
        await asyncio.wait_for(app.finished.wait(), timeout=1)


@pytest.mark.asyncio
async def test_close_before_shortcut_wrapper_starts_and_closed_document_rejects_new_work(tmp_path):
    source = project(tmp_path, '<button id="button" on-pressed="refresh"/>', '''
from textui import command
@command(shortcut="ctrl+r")
def refresh():
    window.app.calls.append("called")
''')
    app = ProjectApp(source)
    app.calls = []
    async with app.run_test() as pilot:
        button = app.document.get_by_id("button")
        app.document.start_command("refresh")
        app.document.close()
        app.document.close()
        await pilot.pause()
        assert app.calls == []
        assert await app.document.dispatch(Button.Pressed(button)) is False
        with pytest.raises(DocumentStateError, match="closed"):
            await app.document.invoke_command("refresh")
        tasks = asyncio.all_tasks()
        app.document.start_command("refresh")
        assert asyncio.all_tasks() == tasks
        await pilot.pause()
        assert app.calls == []


@pytest.mark.asyncio
async def test_project_exit_ignores_queued_events_before_unmount(tmp_path):
    source = project(tmp_path, '<button id="button" on-pressed="refresh"/>', '''
from textui import action
@action
def refresh(context):
    window.app.calls.append("called")
''')
    app = ProjectApp(source)
    app.calls = []
    async with app.run_test():
        event = Button.Pressed(app.document.get_by_id("button"))
        app.exit()
        assert app.window.phase == "closing"
        assert await app.document.dispatch(event) is False
    assert app.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("first_to_finish", [0, 1])
async def test_action_and_command_share_target_loading_in_both_completion_orders(tmp_path, first_to_finish):
    source = project(tmp_path, '<button id="button" on-pressed="first"/><label id="status"/>', '''
from textui import action, command
@action(target="status", supersede=True)
async def first(context):
    window.app.started[0].set()
    await window.app.releases[0].wait()
@command(target="status", supersede=True)
async def second():
    window.app.started[1].set()
    await window.app.releases[1].wait()
''')
    app = ProjectApp(source)
    app.started = [asyncio.Event(), asyncio.Event()]
    app.releases = [asyncio.Event(), asyncio.Event()]
    async with app.run_test() as pilot:
        await app.document.dispatch(Button.Pressed(app.document.get_by_id("button")))
        command_task = asyncio.create_task(app.document.invoke_command("second"))
        try:
            await asyncio.gather(*(event.wait() for event in app.started))
            status = app.document.get_by_id("status")
            app.releases[first_to_finish].set()
            if first_to_finish == 1:
                assert await command_task
            await pilot.pause()
            assert status.has_class("-loading")
            app.releases[1 - first_to_finish].set()
            assert await command_task
            await pilot.pause()
            assert not status.has_class("-loading")
            assert not status.has_class("-error")
        finally:
            for release in app.releases:
                release.set()
            await asyncio.gather(command_task, return_exceptions=True)
            await pilot.pause()


@pytest.mark.asyncio
async def test_superseded_command_failure_does_not_publish_stale_target_error(tmp_path):
    source = project(tmp_path, '<label id="status"/>', '''
import asyncio
from textui import command
@command(target="status", supersede=True)
async def refresh():
    index = window.app.calls
    window.app.calls += 1
    window.app.started[index].set()
    if index == 0:
        try:
            await window.app.releases[0].wait()
        except asyncio.CancelledError:
            window.app.cancelled.set()
            await window.app.releases[0].wait()
        raise window.app.original_error
    await window.app.releases[1].wait()
''')
    app = ProjectApp(source)
    app.calls = 0
    app.started = [asyncio.Event(), asyncio.Event()]
    app.releases = [asyncio.Event(), asyncio.Event()]
    app.cancelled = asyncio.Event()
    app.original_error = ValueError("stale failure")
    async with app.run_test():
        first = asyncio.create_task(app.document.invoke_command("refresh"))
        await app.started[0].wait()
        second = asyncio.create_task(app.document.invoke_command("refresh"))
        try:
            await app.started[1].wait()
            await app.cancelled.wait()
            app.releases[1].set()
            assert await second
            app.releases[0].set()
            with pytest.raises(ActionExecutionError) as caught:
                await first
            assert caught.value.__cause__ is app.original_error
            assert caught.value.location.source.endswith("controller.py")
            status = app.document.get_by_id("status")
            assert not status.has_class("-loading")
            assert not status.has_class("-error")
            assert status.textui_error is None
        finally:
            for release in app.releases:
                release.set()
            await asyncio.gather(first, second, return_exceptions=True)


@pytest.mark.asyncio
async def test_window_copy_requires_ready_and_selection_action_uses_clipboard(tmp_path, monkeypatch):
    from unittest.mock import AsyncMock
    import textui.clipboard as clipboard_module

    copy = AsyncMock(return_value="pbcopy")
    monkeypatch.setattr(clipboard_module, "copy_to_clipboard", copy)
    source = project(tmp_path, '<log id="transcript" on-selection-ended="copy_selection"/>', '''
from textui import action

def on_ready():
    window.document.get_by_id("transcript").append("FIRST word")

@action
async def copy_selection(context):
    window.app.backend = await window.copy(context.event.text)
''')
    app = ProjectApp(source)
    with pytest.raises(DocumentStateError, match="ready"):
        await app.window.copy("not ready")
    async with app.run_test() as pilot:
        log = app.document.get_by_id("transcript")
        await pilot.mouse_down(log, offset=(0, 0))
        await pilot.hover(log, offset=(4, 0))
        await pilot.mouse_up(log, offset=(4, 0))
        await pilot.pause()
        await app.workers.wait_for_complete()
        copy.assert_awaited_once_with(app, "FIRST")
        assert app.backend == "pbcopy"
    with pytest.raises(DocumentStateError, match="ready"):
        await app.window.copy("closed")


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
async def test_command_shortcut_starts_superseding_work_without_blocking_input(tmp_path: Path):
    source = project(tmp_path, '<label id="status">Ready</label>', '''
import asyncio
from textui import command

@command(shortcut="ctrl+r", target="status", supersede=True)
async def refresh():
    window.app.calls += 1
    if window.app.calls == 1:
        window.app.first_started.set()
    else:
        window.app.second_started.set()
    await window.app.release.wait()
''')
    app = ProjectApp(source)
    app.calls = 0
    app.first_started = asyncio.Event()
    app.second_started = asyncio.Event()
    app.release = asyncio.Event()

    async with app.run_test() as pilot:
        first_press = asyncio.create_task(pilot.press("ctrl+r"))
        await app.first_started.wait()
        second_press = asyncio.create_task(pilot.press("ctrl+r"))
        try:
            await asyncio.wait_for(app.second_started.wait(), timeout=0.2)
        finally:
            app.release.set()
            await asyncio.gather(first_press, second_press)
        assert app.calls == 2


@pytest.mark.asyncio
async def test_concurrent_command_lifecycle_keeps_loading_until_every_task_finishes(tmp_path: Path):
    source = project(tmp_path, '<label id="status">Ready</label>', '''
import asyncio
from textui import command

@command(target="status")
async def refresh():
    index = window.app.calls
    window.app.calls += 1
    window.app.started[index].set()
    await window.app.releases[index].wait()
''')
    app = ProjectApp(source)
    app.calls = 0
    app.started = [asyncio.Event(), asyncio.Event()]
    app.releases = [asyncio.Event(), asyncio.Event()]

    async with app.run_test() as pilot:
        first = asyncio.create_task(app.document.invoke_command("refresh"))
        second = asyncio.create_task(app.document.invoke_command("refresh"))
        await asyncio.gather(*(started.wait() for started in app.started))
        app.releases[1].set()
        assert await second is True
        assert app.document.get_by_id("status").has_class("-loading")
        app.releases[0].set()
        assert await first is True
        await pilot.pause()
        assert not app.document.get_by_id("status").has_class("-loading")


@pytest.mark.asyncio
async def test_document_close_cancels_every_concurrent_command_lifecycle_task(tmp_path: Path):
    source = project(tmp_path, '<label id="status">Ready</label>', '''
import asyncio
from textui import command

@command(target="status")
async def refresh():
    index = window.app.calls
    window.app.calls += 1
    window.app.started[index].set()
    await window.app.release.wait()
''')
    app = ProjectApp(source)
    app.calls = 0
    app.started = [asyncio.Event(), asyncio.Event()]
    app.release = asyncio.Event()

    async with app.run_test():
        first = asyncio.create_task(app.document.invoke_command("refresh"))
        second = asyncio.create_task(app.document.invoke_command("refresh"))
        await asyncio.gather(*(started.wait() for started in app.started))
        app.document.close()
        done, pending = await asyncio.wait({first, second}, timeout=0.2)
        try:
            assert not pending
            assert all(task.cancelled() for task in done)
            assert not app.document.get_by_id("status").has_class("-loading")
        finally:
            app.release.set()
            await asyncio.gather(first, second, return_exceptions=True)


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


@pytest.mark.asyncio
async def test_host_context_is_available_at_script_load_and_read_only_on_window(tmp_path: Path):
    source = project(tmp_path, '<label>Hi</label>', '''
window.app.events.append(("load", window.context))

def on_setup():
    window.app.events.append(("setup", window.context))
    try:
        window.context = object()
    except AttributeError:
        window.app.events.append(("read-only", window.context))
''')
    host_context = {"account": "demo"}
    app = ProjectApp(source, context=host_context)
    app.events = []

    async with app.run_test():
        assert app.events == [
            ("load", host_context),
            ("setup", host_context),
            ("read-only", host_context),
        ]
        assert app.window.context is host_context


@pytest.mark.asyncio
async def test_resize_hook_sees_settled_screen_and_widget_size(tmp_path: Path):
    source = project(tmp_path, '<label id="status" style="width: 100%;">Hi</label>', '''
async def on_resize(width, height):
    status = window.document.get_by_id("status")
    window.app.resizes.append((width, height, window.app.screen.size.width, status.size.width))
''')
    app = ProjectApp(source)
    app.resizes = []

    async with app.run_test() as pilot:
        await pilot.pause()
        assert len(app.resizes) <= 1
        await pilot.resize_terminal(60, 20)
        await pilot.pause()
        assert app.resizes[-1] == (60, 20, 60, 60)
        count = len(app.resizes)
        await pilot.resize_terminal(78, 25)
        await pilot.pause()
        assert app.resizes[-1] == (78, 25, 78, 78)
        assert len(app.resizes) == count + 1
        assert all(width == screen_width == widget_width for width, _, screen_width, widget_width in app.resizes)


@pytest.mark.asyncio
@pytest.mark.parametrize("screen_style", ["padding: 1;", "border: solid red;", "padding: 1; border: solid red;"])
async def test_resize_hook_uses_terminal_dimensions_with_screen_gutters(tmp_path: Path, screen_style: str):
    source = project(tmp_path, f'''<style>Screen {{ {screen_style} }}</style>
      <label id="status" style="width: 100%;">Hi</label>''', '''
def on_resize(width, height):
    status = window.document.get_by_id("status")
    window.app.resizes.append((width, height, status.size.width))
''')
    app = ProjectApp(source)
    app.resizes = []

    async with app.run_test() as pilot:
        await pilot.resize_terminal(60, 20)
        await pilot.pause()
        assert app.resizes
        assert app.resizes[-1][:2] == (60, 20)
        assert app.resizes[-1][2] == app.document.get_by_id("status").size.width < 60


@pytest.mark.asyncio
async def test_resize_hook_rejects_wrong_signature_with_source_context(tmp_path: Path):
    source = project(tmp_path, '<label>Hi</label>', '''
def on_resize(width):
    pass
''')
    app = ProjectApp(source)
    with pytest.raises(DocumentValidationError, match="unsupported signature for on_resize") as caught:
        async with app.run_test():
            pass
    assert "controller.py" in str(caught.value)


@pytest.mark.asyncio
async def test_queued_resize_hook_skips_stale_dimensions(tmp_path: Path):
    source = project(tmp_path, '<label id="status" style="width: 100%;">Hi</label>', '''
def on_resize(width, height):
    status = window.document.get_by_id("status")
    window.app.resizes.append((width, height, window.app.screen.size.width, status.size.width))
''')
    app = ProjectApp(source)
    app.resizes = []

    async with app.run_test(size=(80, 24)) as pilot:
        app.post_message(Resize(Size(60, 20), Size(60, 20)))
        app.post_message(Resize(Size(70, 22), Size(70, 22)))
        await pilot.pause()
        assert app.resizes[-1] == (70, 22, 70, 70)
        assert all(width == screen_width == widget_width for width, _, screen_width, widget_width in app.resizes)


@pytest.mark.asyncio
async def test_resize_hook_stops_after_exit(tmp_path: Path):
    source = project(tmp_path, '<label>Hi</label>', '''
def on_resize(width, height):
    window.app.resizes.append((width, height))
''')
    app = ProjectApp(source)
    app.resizes = []

    async with app.run_test() as pilot:
        await pilot.resize_terminal(60, 20)
        assert app.resizes[-1] == (60, 20)
        app.exit()
        await pilot.resize_terminal(70, 22)
    assert (70, 22) not in app.resizes


@pytest.mark.asyncio
async def test_resize_hook_error_preserves_script_source(tmp_path: Path):
    source = project(tmp_path, '<label>Hi</label>', '''
def on_resize(width, height):
    raise ValueError("cannot repaint")
''')
    app = ProjectApp(source)
    with pytest.raises(Exception, match="on_resize.*cannot repaint") as caught:
        async with app.run_test() as pilot:
            await pilot.resize_terminal(60, 20)
    assert "controller.py" in str(caught.value)
