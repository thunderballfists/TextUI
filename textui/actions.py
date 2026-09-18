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
class ActionContext:
    event: Message
    widget: Widget
    app: App
    document: BoundDocument


ActionCallback = Callable[[ActionContext], None | Awaitable[None]]
