import asyncio
from pathlib import Path

import pytest

from textui import DocumentStateError, every
from textui.project import ProjectSource
from textui.project_app import ProjectApp


def app_from(tmp_path: Path, script: str) -> ProjectApp:
    (tmp_path / "app.ui").write_text('<ui><script src="controller.py"/><label id="status">Ready</label></ui>', encoding="utf-8")
    (tmp_path / "controller.py").write_text(script, encoding="utf-8")
    app = ProjectApp(ProjectSource.discover(tmp_path / "app.ui"))
    app.events = []
    return app


@pytest.mark.parametrize("seconds", [0, -1, float("nan"), float("inf")])
def test_every_rejects_nonpositive_or_nonfinite_intervals(seconds):
    with pytest.raises(ValueError):
        every(seconds)


@pytest.mark.asyncio
async def test_ready_starts_decorated_timer_and_one_shot_returns_handle(tmp_path: Path):
    app = app_from(tmp_path, '''
from textui import every

def on_ready():
    window.app.handle = window.after(0.01, lambda: window.app.events.append("once"))

@every(0.01)
def tick():
    window.app.events.append("tick")
''')
    with pytest.raises(DocumentStateError):
        app.window.after(0.01, lambda: None)
    async with app.run_test() as pilot:
        await pilot.pause(0.06)
        assert app.events.count("once") == 1
        assert app.events.count("tick") >= 2
        assert all(hasattr(app.handle, name) for name in ("pause", "resume", "stop"))


@pytest.mark.asyncio
async def test_async_periodic_work_skips_ticks_while_busy_and_keeps_app_responsive(tmp_path: Path):
    app = app_from(tmp_path, '''
import asyncio
from textui import every

@every(0.01)
async def slow():
    window.app.events.append("start")
    await asyncio.sleep(0.04)
    window.app.events.append("end")
''')
    async with app.run_test() as pilot:
        await pilot.pause(0.025)
        app.events.append("responsive")
        await pilot.pause(0.035)
        assert app.events[:2] == ["start", "responsive"]
        assert app.events.count("start") <= 2


@pytest.mark.asyncio
async def test_threaded_callback_marshals_ui_update(tmp_path: Path):
    app = app_from(tmp_path, '''
from textui import every

@every(0.01, thread=True)
def update():
    window.call_ui(lambda: window.app.events.append("ui"))
''')
    async with app.run_test() as pilot:
        await pilot.pause(0.04)
        assert "ui" in app.events


@pytest.mark.asyncio
async def test_owned_timers_stop_on_close(tmp_path: Path):
    app = app_from(tmp_path, '''
from textui import every

@every(0.01)
def tick():
    window.app.events.append("tick")
''')
    async with app.run_test() as pilot:
        await pilot.pause(0.035)
    before = len(app.events)
    await asyncio.sleep(0.035)
    assert len(app.events) == before


@pytest.mark.asyncio
async def test_exit_stops_owned_timers_before_unmount(tmp_path: Path):
    app = app_from(tmp_path, '''
from textui import every

@every(0.01)
def tick():
    window.app.events.append("tick")
''')
    async with app.run_test() as pilot:
        await pilot.pause(0.025)
        app.exit()
        before = len(app.events)
        await pilot.pause(0.035)
        assert len(app.events) == before


@pytest.mark.asyncio
async def test_sync_callback_returning_awaitable_does_not_overlap(tmp_path: Path):
    app = app_from(tmp_path, '''
import asyncio
from textui import every

async def delayed():
    window.app.events.append("start")
    await asyncio.sleep(0.04)
    window.app.events.append("end")

@every(0.01)
def tick():
    return delayed()
''')
    async with app.run_test() as pilot:
        await pilot.pause(0.06)
        assert app.events[:3] == ["start", "end", "start"]
