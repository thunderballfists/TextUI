"""Private ownership of action and command work within a bound document."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from textual.widget import Widget

from .actions import ActionInvocation
from .errors import DocumentStateError


@dataclass(eq=False, slots=True)
class OwnedInvocation:
    name: str
    state: ActionInvocation
    generation: int
    task: asyncio.Future[object] | None = None
    finished: bool = False


class InvocationOwner:
    def __init__(self) -> None:
        self._closed = False
        self._generation = 0
        self._active: set[OwnedInvocation] = set()
        self._keys: dict[tuple[str, Widget | None], set[OwnedInvocation]] = {}
        self._targets: dict[Widget, set[OwnedInvocation]] = {}
        self._latest: dict[Widget, int] = {}

    @property
    def closed(self) -> bool:
        return self._closed

    def begin(self, name: str, target: Widget | None, *, supersede: bool) -> OwnedInvocation:
        if self.closed:
            raise DocumentStateError("Document is closed")
        self._generation += 1
        invocation = OwnedInvocation(name, ActionInvocation(target), self._generation)
        key = (name, target)
        previous = tuple(self._keys.get(key, ())) if supersede else ()
        self._active.add(invocation)
        self._keys.setdefault(key, set()).add(invocation)
        if target is not None:
            self._targets.setdefault(target, set()).add(invocation)
            self._latest[target] = invocation.generation
            target.add_class("-loading")
            target.remove_class("-error")
            target.textui_error = None
        # Register replacement ownership before requesting old-task cancellation.
        for old in previous:
            if old.task is not None and old.task.done():
                continue
            old.state.cancelled = True
            if old.task is not None:
                old.task.cancel()
        return invocation

    def track(self, invocation: OwnedInvocation, task: asyncio.Future[object]) -> None:
        if not invocation.finished:
            invocation.task = task
        if self.closed or invocation.state.cancelled:
            task.cancel()

        def completed(future: asyncio.Future[object]) -> None:
            if future.cancelled():
                invocation.state.cancelled = True
                self.finish(invocation)
            else:
                error = future.exception()
                self.finish(invocation, error if isinstance(error, Exception) else None)

        task.add_done_callback(completed)

    def finish(self, invocation: OwnedInvocation, error: Exception | None = None) -> None:
        if invocation.finished:
            return
        invocation.finished = True
        invocation.task = None
        self._active.discard(invocation)
        target = invocation.state.target
        key = (invocation.name, target)
        keyed = self._keys.get(key)
        if keyed is not None:
            keyed.discard(invocation)
            if not keyed:
                self._keys.pop(key)
        if target is None:
            return
        active = self._targets.get(target)
        if active is None:
            return
        active.discard(invocation)
        if error is not None and self._latest.get(target) == invocation.generation:
            target.textui_error = str(error)
            target.add_class("-error")
        if not active:
            target.remove_class("-loading")
            self._targets.pop(target)
            self._latest.pop(target, None)

    def close(self) -> None:
        if self.closed:
            return
        self._closed = True
        active = tuple(self._active)
        for invocation in active:
            invocation.state.cancelled = True
            invocation.finished = True
            if invocation.task is not None and not invocation.task.done():
                invocation.task.cancel()
            invocation.task = None
        for target in self._targets:
            target.remove_class("-loading")
        self._active.clear()
        self._keys.clear()
        self._targets.clear()
        self._latest.clear()
