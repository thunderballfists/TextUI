"""A native two-pane Textual container with a captured draggable divider."""
from __future__ import annotations

from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.events import MouseDown, MouseMove, MouseUp
from textual.message import Message
from textual.widgets import Static


class Pane(Vertical):
    def __init__(self, *children, min_size: int = 1, size: int | None = None) -> None:
        super().__init__(*children)
        self.min_size = min_size
        self.preferred_size = size

    def on_hide(self) -> None:
        if isinstance(self.parent, Split):
            self.parent.pane_visibility_changed()

    def on_show(self) -> None:
        if isinstance(self.parent, Split):
            self.parent.pane_visibility_changed()


class Divider(Static):
    can_focus = True
    BINDINGS = [
        Binding("left", "shrink", "Shrink", show=False),
        Binding("up", "shrink", "Shrink", show=False),
        Binding("right", "grow", "Grow", show=False),
        Binding("down", "grow", "Grow", show=False),
    ]

    def __init__(self, direction: str) -> None:
        super().__init__("│" if direction == "horizontal" else "─")
        self.direction = direction
        self._dragging = False

    def on_mouse_down(self, event: MouseDown) -> None:
        if event.button != 1:
            return
        self._dragging = True
        self.capture_mouse()
        event.stop()

    def on_mouse_move(self, event: MouseMove) -> None:
        if self._dragging and isinstance(self.parent, Split):
            coordinate = event.screen_x if self.direction == "horizontal" else event.screen_y
            origin = self.parent.region.x if self.direction == "horizontal" else self.parent.region.y
            self.parent.resize_first(coordinate - origin)
            event.stop()

    def on_mouse_up(self, event: MouseUp) -> None:
        if self._dragging:
            self._dragging = False
            self.release_mouse()
            event.stop()

    def action_shrink(self) -> None:
        if isinstance(self.parent, Split):
            self.parent.resize_first(self.parent.first_size - 1)

    def action_grow(self) -> None:
        if isinstance(self.parent, Split):
            self.parent.resize_first(self.parent.first_size + 1)


class Split(Container):
    DEFAULT_CSS = "Split { width: 100%; height: 100%; }"

    class Resized(Message):
        def __init__(self, split: Split, size: int) -> None:
            super().__init__()
            self.split = split
            self.size = size

    class Toggled(Message):
        def __init__(self, split: Split, visible: bool) -> None:
            super().__init__()
            self.split = split
            self.visible = visible

    def __init__(self, first: Pane, second: Pane, *, direction: str = "horizontal") -> None:
        self.first = first
        self.second = second
        self.direction = direction
        self.divider = Divider(direction)
        self.first_size = first.preferred_size
        super().__init__(first, self.divider, second)
        self.styles.layout = direction

    def on_mount(self) -> None:
        self._apply()

    def on_resize(self) -> None:
        self._apply()

    def pane_visibility_changed(self) -> None:
        self._apply()
        self.post_message(self.Toggled(self, self.first.display and self.second.display))

    def resize_first(self, size: int) -> None:
        if self.first_size != size:
            self.first_size = size
            self._apply()
            self.post_message(self.Resized(self, self.first_size))

    def _apply(self) -> None:
        both = self.first.display and self.second.display
        self.divider.display = both
        dimension = self.size.width if self.direction == "horizontal" else self.size.height
        axis = "width" if self.direction == "horizontal" else "height"
        if dimension <= 1:
            return
        if both:
            available = max(0, dimension - 1)
            lower = min(self.first.min_size, available)
            upper = max(lower, available - self.second.min_size)
            if self.first_size is None:
                self.first_size = available // 2
            self.first_size = max(lower, min(self.first_size, upper))
            setattr(self.first.styles, axis, self.first_size)
            setattr(self.second.styles, axis, "1fr")
            if self.direction == "horizontal":
                self.divider.styles.width = 1
                self.divider.styles.height = "100%"
                self.first.styles.height = self.second.styles.height = "100%"
            else:
                self.divider.styles.height = 1
                self.divider.styles.width = "100%"
                self.first.styles.width = self.second.styles.width = "100%"
        else:
            visible = self.first if self.first.display else self.second
            setattr(visible.styles, axis, "1fr")
