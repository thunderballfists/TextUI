import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from textui import copy_to_clipboard
from textui import clipboard as clipboard_module


def backend(monkeypatch, platform, available, processes):
    monkeypatch.setattr(clipboard_module.sys, "platform", platform)
    monkeypatch.setattr(clipboard_module.shutil, "which", lambda name: f"/tools/{name}" if name in available else None)
    spawn = AsyncMock(side_effect=processes)
    monkeypatch.setattr(clipboard_module.asyncio, "create_subprocess_exec", spawn)
    app = SimpleNamespace(copy_to_clipboard=Mock())
    return app, spawn


def process(code=0):
    return SimpleNamespace(returncode=code, communicate=AsyncMock(return_value=(b"", b"")), kill=Mock(), wait=AsyncMock())


@pytest.mark.asyncio
async def test_mac_native_copy_uses_unicode_stdin_and_also_sends_terminal_transport(monkeypatch):
    monkeypatch.setenv("LC_ALL", "C")
    child = process()
    app, spawn = backend(monkeypatch, "darwin", {"pbcopy"}, [child])
    assert await copy_to_clipboard(app, "café 🐍") == "pbcopy"
    assert spawn.call_args.args == ("/tools/pbcopy",)
    assert spawn.call_args.kwargs["env"]["LC_CTYPE"] == "UTF-8"
    assert "LC_ALL" not in spawn.call_args.kwargs["env"]
    child.communicate.assert_awaited_once_with("café 🐍".encode("utf-8"))
    app.copy_to_clipboard.assert_called_once_with("café 🐍")


@pytest.mark.asyncio
async def test_windows_clip_receives_utf16_with_bom(monkeypatch):
    child = process()
    app, spawn = backend(monkeypatch, "win32", {"clip"}, [child])
    assert await copy_to_clipboard(app, "café 🐍") == "clip"
    assert spawn.call_args.args == ("/tools/clip",)
    child.communicate.assert_awaited_once_with(b"\xff\xfe" + "café 🐍".encode("utf-16-le"))


@pytest.mark.asyncio
async def test_wayland_failure_falls_through_to_x11(monkeypatch):
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    first, second = process(1), process()
    app, spawn = backend(monkeypatch, "linux", {"wl-copy", "xclip", "xsel"}, [first, second])
    assert await copy_to_clipboard(app, "hello") == "xclip"
    assert [call.args for call in spawn.call_args_list] == [("/tools/wl-copy",), ("/tools/xclip", "-selection", "clipboard")]


@pytest.mark.asyncio
async def test_x11_prefers_xclip_without_wayland_display(monkeypatch):
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    app, spawn = backend(monkeypatch, "linux", {"wl-copy", "xclip"}, [process()])
    assert await copy_to_clipboard(app, "hello") == "xclip"
    assert spawn.call_args.args[0] == "/tools/xclip"


@pytest.mark.asyncio
async def test_missing_or_failed_native_backend_reports_osc52(monkeypatch):
    app, spawn = backend(monkeypatch, "darwin", {"pbcopy"}, [OSError("unavailable")])
    assert await copy_to_clipboard(app, "hello") == "osc52"
    app.copy_to_clipboard.assert_called_once_with("hello")
    app, spawn = backend(monkeypatch, "darwin", set(), [])
    assert await copy_to_clipboard(app, "") == "osc52"
    spawn.assert_not_called()
    app.copy_to_clipboard.assert_called_once_with("")


@pytest.mark.asyncio
async def test_timeout_kills_and_reaps_before_fallback(monkeypatch):
    child = process()
    async def communicate(payload):
        await asyncio.Event().wait()
    child.communicate.side_effect = communicate
    monkeypatch.setattr(clipboard_module, "_COPY_TIMEOUT", 0.01)
    app, _ = backend(monkeypatch, "darwin", {"pbcopy"}, [child])
    assert await copy_to_clipboard(app, "hello") == "osc52"
    child.kill.assert_called_once()
    child.wait.assert_awaited_once()


@pytest.mark.asyncio
async def test_copy_keeps_event_loop_running_and_cancellation_reaps_child(monkeypatch):
    started = asyncio.Event()
    async def communicate(payload):
        started.set()
        await asyncio.Event().wait()
    child = process()
    child.communicate.side_effect = communicate
    app, _ = backend(monkeypatch, "darwin", {"pbcopy"}, [child])
    task = asyncio.create_task(copy_to_clipboard(app, "hello"))
    await asyncio.wait_for(started.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    child.kill.assert_called_once()
    child.wait.assert_awaited_once()
    app.copy_to_clipboard.assert_not_called()


@pytest.mark.asyncio
async def test_copy_requires_text(monkeypatch):
    app, spawn = backend(monkeypatch, "darwin", {"pbcopy"}, [])
    with pytest.raises(TypeError, match="text"):
        await copy_to_clipboard(app, None)
    spawn.assert_not_called()
    app.copy_to_clipboard.assert_not_called()
