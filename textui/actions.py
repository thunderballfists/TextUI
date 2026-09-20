"""Explicit Python callbacks exposed to a bound document."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from textual.app import App
from textual.message import Message
from textual.widget import Widget

if TYPE_CHECKING:
    from .document import BoundDocument


@dataclass(frozen=True, slots=True)
class ActionOptions:
    target: str | None = None
    supersede: bool = False


@dataclass(slots=True)
class ActionInvocation:
    target: Widget | None = None
    cancelled: bool = False


@dataclass(frozen=True, slots=True)
class ActionContext:
    event: Message
    widget: Widget
    app: App
    document: BoundDocument
    _invocation: ActionInvocation | None = None

    @property
    def target(self) -> Widget | None:
        return self._invocation.target if self._invocation is not None else None

    @property
    def cancelled(self) -> bool:
        return self._invocation.cancelled if self._invocation is not None else False

    def push_modal(self, modal_id: str):
        """Push a declared modal and return its awaitable dismissal value."""
        return self.document.push_modal(modal_id)

    def dismiss_modal(self, value: object | None = None) -> None:
        """Dismiss the active declared modal with an optional value."""
        self.document.dismiss_modal(value)


ActionCallback = Callable[[ActionContext], None | Awaitable[None]]
