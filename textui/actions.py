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


@dataclass(frozen=True, slots=True)
class ActionContext:
    event: Message
    widget: Widget
    app: App
    document: BoundDocument
    _target: Widget | None = None
    _cancelled: bool = False

    @property
    def target(self) -> Widget | None:
        return self._target

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def push_modal(self, modal_id: str):
        """Push a declared modal and return its awaitable dismissal value."""
        return self.document.push_modal(modal_id)

    def dismiss_modal(self, value: object | None = None) -> None:
        """Dismiss the active declared modal with an optional value."""
        self.document.dismiss_modal(value)


ActionCallback = Callable[[ActionContext], None | Awaitable[None]]
