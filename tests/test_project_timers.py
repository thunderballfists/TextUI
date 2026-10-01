import asyncio
from pathlib import Path
import threading

import pytest
from textual.worker import Worker, WorkerCancelled, WorkerFailed, WorkerState, get_current_worker

from textui import DocumentStateError, TextUIError, every
from textui.project import ProjectSource
from textui.project_app import ProjectApp


def app_from(tmp_path: Path, script: str, app_type=ProjectApp) -> ProjectApp:
    (tmp_path / "app.ui").write_text('<ui><script src="controller.py"/><label id="status">Ready</label></ui>', encoding="utf-8")
    (tmp_path / "controller.py").write_text(script, encoding="utf-8")
    app = app_type(ProjectSource.discover(tmp_path / "app.ui"))
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
async def test_ready_exit_skips_periodic_timer_startup(tmp_path: Path):
    app = app_from(tmp_path, '''
from textui import every

def on_ready():
    window.app.exit()

@every(0.01)
def tick():
    window.app.events.append("tick")
''')

    async with app.run_test():
        pass

    assert app.events == []


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
        assert app.events[:2] == ["start", "end"]



@pytest.mark.asyncio
async def test_timer_stands_down_once_the_message_pump_stops(tmp_path: Path):
    """A tick scheduled during teardown must not reach an unmounted document.

    `window.phase` only leaves "ready" once the app's own teardown hooks run,
    which is after Textual has begun removing widgets. A timer firing in that
    window previously reached elements that were already unmounted and raised
    DocumentStateError out of the timer.
    """
    app = app_from(tmp_path, '''
from textui import every

@every(0.01)
def touch_status() -> None:
    window.document.get_by_id("status").update("tick")
    window.app.events.append("tick")
''')
    async with app.run_test() as pilot:
        await pilot.pause(0.05)
        assert app.events.count("tick") >= 1
        # Simulate the teardown window: the pump has stopped but the phase has
        # not yet been moved on by the app's unmount hook.
        app._running = False
        before = len(app.events)
        await pilot.pause(0.05)
        assert len(app.events) == before, "timer fired after the message pump stopped"
        app._running = True


@pytest.mark.asyncio
@pytest.mark.parametrize("thread", [False, True])
async def test_completed_timer_workers_are_released_after_twenty_ticks(tmp_path, thread):
    app = app_from(tmp_path, "")
    completed = asyncio.Event()
    observed = []

    def record(worker):
        observed.append(worker)
        if len(observed) >= 20:
            handle.stop()
            completed.set()

    async def asynchronous():
        record(get_current_worker())
        await asyncio.sleep(0)

    def threaded():
        app.call_from_thread(record, get_current_worker())

    async with app.run_test() as pilot:
        handle = app.window.every(0.001, threaded if thread else asynchronous, thread=thread)
        await asyncio.wait_for(completed.wait(), timeout=3)
        await asyncio.gather(*(worker.wait() for worker in observed))
        await pilot.pause()
        assert len(observed) >= 20
        assert all(worker.is_finished for worker in observed)
        assert app.window.timers.workers == set()
        app.window.timers.close()
        app.window.timers.close()
        assert app.window.timers.handles == []


@pytest.mark.asyncio
@pytest.mark.parametrize("thread", [False, True])
async def test_timer_registration_releases_a_worker_that_already_finished(tmp_path, thread):
    app = app_from(tmp_path, "")

    async def asynchronous():
        return None

    async with app.run_test() as pilot:
        worker = app.run_worker((lambda: None) if thread else asynchronous(), thread=thread)
        await worker.wait()
        app.window.timers._own_worker(worker)
        assert app.window.timers.workers == set()
        await pilot.pause()
        assert app.window.timers.workers == set()


@pytest.mark.asyncio
async def test_timer_close_releases_active_workers_and_ignores_unrelated_and_late_messages(tmp_path):
    app = app_from(tmp_path, "")
    started, release = asyncio.Event(), asyncio.Event()
    observed = []

    async def tick():
        observed.append(get_current_worker())
        started.set()
        await release.wait()

    async def unrelated():
        return "host work"

    async with app.run_test() as pilot:
        app.window.after(0.001, tick)
        await asyncio.wait_for(started.wait(), timeout=1)
        owned = observed[0]
        host_worker = app.run_worker(unrelated())
        assert await host_worker.wait() == "host work"
        await pilot.pause()
        assert app.window.timers.workers == {owned}
        app.window.timers.close()
        app.window.timers.close()
        assert app.window.timers.handles == []
        assert app.window.timers.workers == set()
        with pytest.raises(WorkerCancelled):
            await owned.wait()
        await pilot.pause()
        app.window.timers.handle_worker_state(Worker.StateChanged(owned, WorkerState.CANCELLED))
        app.window.timers.handle_worker_state(Worker.StateChanged(host_worker, WorkerState.SUCCESS))
        assert app.window.timers.workers == set()


class _CapturingTimerApp(ProjectApp):
    def __init__(self, source):
        super().__init__(source)
        self.errors = []

    def _handle_exception(self, error):
        self.errors.append(error)


@pytest.mark.asyncio
@pytest.mark.parametrize("thread", [False, True])
async def test_cancelled_timer_workers_are_released_before_app_close(tmp_path, thread):
    app = app_from(tmp_path, "", _CapturingTimerApp)
    started = asyncio.Event()
    release = threading.Event() if thread else asyncio.Event()
    observed = []

    def record(worker):
        observed.append(worker)
        started.set()

    async def asynchronous():
        record(get_current_worker())
        await release.wait()

    def threaded():
        app.call_from_thread(record, get_current_worker())
        release.wait()

    async with app.run_test() as pilot:
        try:
            app.window.timers.schedule(0.001, threaded if thread else asynchronous, repeat=False, thread=thread)
            await asyncio.wait_for(started.wait(), timeout=1)
            worker = observed[0]
            worker.cancel()
            with pytest.raises(WorkerCancelled):
                await worker.wait()
            await pilot.pause()
            assert app.window.timers.workers == set()
            assert app.errors == []
        finally:
            release.set()


@pytest.mark.asyncio
@pytest.mark.parametrize("thread", [False, True])
async def test_failed_timer_workers_are_released_without_suppressing_native_errors(tmp_path, thread):
    app = app_from(tmp_path, "", _CapturingTimerApp)
    started = asyncio.Event()
    observed = []
    original = ValueError("timer failed")

    def record(worker):
        observed.append(worker)
        started.set()

    async def asynchronous():
        record(get_current_worker())
        raise original

    def threaded():
        app.call_from_thread(record, get_current_worker())
        raise original

    async with app.run_test() as pilot:
        app.window.timers.schedule(0.001, threaded if thread else asynchronous, repeat=False, thread=thread)
        await asyncio.wait_for(started.wait(), timeout=1)
        with pytest.raises(WorkerFailed):
            await observed[0].wait()
        await pilot.pause()
        assert app.window.timers.workers == set()
        assert len(app.errors) == 1
        assert isinstance(app.errors[0], WorkerFailed)
        error = app.errors[0].error
        assert isinstance(error, TextUIError)
        assert error.__cause__ is original
        assert error.location.source == __file__
