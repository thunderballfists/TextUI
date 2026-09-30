"""Asynchronous native clipboard tools with Textual's terminal transport."""
from __future__ import annotations

import asyncio
import os
import shutil
import sys

from textual.app import App

_COPY_TIMEOUT = 2.0


def _candidates() -> tuple[tuple[str, ...], ...]:
    if sys.platform == "darwin":
        return (("pbcopy",),)
    if sys.platform == "win32":
        return (("clip",),)
    x11 = (("xclip", "-selection", "clipboard"), ("xsel", "--clipboard", "--input"))
    return (("wl-copy",), *x11) if os.environ.get("WAYLAND_DISPLAY") else x11


async def _reap(process: asyncio.subprocess.Process) -> None:
    try:
        process.kill()
    except ProcessLookupError:
        pass
    await process.wait()


async def copy_to_clipboard(app: App, text: str) -> str:
    """Copy text using a native tool and OSC 52; return the native tool or `osc52`.

    OSC 52 delivery depends on the terminal. A return value of `osc52` reports
    that transport was sent, not that the system clipboard accepted it.
    """
    if not isinstance(text, str):
        raise TypeError("clipboard text must be a string")
    backend = "osc52"
    for name, *arguments in _candidates():
        executable = shutil.which(name)
        if executable is None:
            continue
        payload = text.encode("utf-8")
        environment = os.environ.copy()
        if name == "pbcopy":
            environment.pop("LC_ALL", None)
            environment["LC_CTYPE"] = "UTF-8"
        elif name == "clip":
            payload = b"\xff\xfe" + text.encode("utf-16-le")
        process = None
        try:
            process = await asyncio.create_subprocess_exec(
                executable, *arguments, stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
                env=environment,
            )
            await asyncio.wait_for(process.communicate(payload), timeout=_COPY_TIMEOUT)
        except asyncio.CancelledError:
            if process is not None:
                await _reap(process)
            raise
        except (OSError, TimeoutError):
            if process is not None:
                await _reap(process)
            continue
        if process.returncode == 0:
            backend = name
            break
    app.copy_to_clipboard(text)
    return backend
