"""Thin Textual timer and worker ownership for linked controllers."""
from __future__ import annotations

from collections.abc import Callable
from inspect import isawaitable, iscoroutinefunction, signature
from math import isfinite
from pathlib import Path
from typing import Any

from .errors import DocumentStateError, SourceLocation, TextUIError


def _seconds(value: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("timer interval must be a positive finite number") from error
    if not isfinite(result) or result <= 0:
        raise ValueError("timer interval must be a positive finite number")
    return result


def every(seconds: float, *, thread: bool = False):
    """Mark a zero-argument controller function as a repeating timer."""
    interval = _seconds(seconds)

    def decorate(function: Callable[[], Any]) -> Callable[[], Any]:
        function.__textui_every__ = (interval, thread)
        return function

    return decorate


class RuntimeTimers:
    def __init__(self, app: Any, window: Any) -> None:
        self.app = app
        self.window = window
        self.handles: list[Any] = []
        self.workers: set[Any] = set()

    def schedule(self, seconds: float, callback: Callable[[], Any], *, repeat: bool, thread: bool = False):
        if self.window.phase != "ready":
            raise DocumentStateError("timers are available only after on_ready begins")
        interval = _seconds(seconds)
        if not callable(callback) or signature(callback).parameters:
            raise ValueError("timer callback must take no arguments")
        if thread and iscoroutinefunction(callback):
            raise ValueError("async timer callbacks cannot use thread=True")
        busy = False
        name = getattr(callback, "__name__", type(callback).__name__)
        code = getattr(callback, "__code__", None)
        location = SourceLocation(str(Path(code.co_filename)), code.co_firstlineno) if code is not None else None

        def run() -> None:
            nonlocal busy
            if busy or self.window.phase != "ready":
                return
            busy = True

            def invoke() -> Any:
                try:
                    return callback()
                except Exception as error:
                    raise TextUIError(f"timer {name} failed: {error}", location=location) from error
                finally:
                    if thread:
                        nonlocal busy
                        busy = False

            if thread:
                worker = self.app.run_worker(invoke, name=f"textui:{name}", thread=True)
                self.workers.add(worker)
                return
            try:
                result = invoke()
                if isawaitable(result):
                    async def await_result():
                        nonlocal busy
                        try:
                            await result
                        except Exception as error:
                            raise TextUIError(f"timer {name} failed: {error}", location=location) from error
                        finally:
                            busy = False
                    worker = self.app.run_worker(await_result(), name=f"textui:{name}")
                    self.workers.add(worker)
                    return
            finally:
                if not iscoroutinefunction(callback):
                    busy = False

        handle = self.app.set_interval(interval, run, name=f"textui:{name}") if repeat else self.app.set_timer(interval, run, name=f"textui:{name}")
        self.handles.append(handle)
        return handle

    def close(self) -> None:
        for handle in self.handles:
            handle.stop()
        for worker in self.workers:
            worker.cancel()
