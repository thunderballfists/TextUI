"""A compact integer range control rendered as a native Textual widget."""
from __future__ import annotations

from typing import ClassVar

from rich.text import Text
from textual.binding import Binding, BindingType
from textual.events import Click, MouseDown, MouseMove, MouseUp
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget


class RangeControl(Widget, can_focus=True):
    """A keyboard and pointer accessible integer range control."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("left,down", "decrease", "Decrease", show=False),
        Binding("right,up", "increase", "Increase", show=False),
        Binding("home", "minimum", "Minimum", show=False),
        Binding("end", "maximum", "Maximum", show=False),
    ]
    COMPONENT_CLASSES: ClassVar[set[str]] = {
        "range--track",
        "range--filled",
        "range--thumb",
        "range--value",
    }
    DEFAULT_CSS = """
    RangeControl {
        width: 100%;
        height: 1;
        pointer: pointer;
    }
    RangeControl > .range--track {
        color: $primary 50%;
    }
    RangeControl > .range--filled {
        color: $primary;
    }
    RangeControl > .range--thumb {
        color: $primary-lighten-2;
    }
    RangeControl > .range--value {
        color: $text;
    }
    RangeControl:focus {
        background: $primary 10%;
    }
    RangeControl:hover > .range--thumb {
        color: $primary-lighten-3;
    }
    """

    value: reactive[int] = reactive(0, init=False)

    class Changed(Message):
        """Posted after the range value changes."""

        def __init__(self, range_control: RangeControl, value: int) -> None:
            super().__init__()
            self.range_control = range_control
            self.value = value

        @property
        def control(self) -> RangeControl:
            """Alias for the range control that emitted the message."""
            return self.range_control

    def __init__(
        self,
        *,
        minimum: int = 0,
        maximum: int = 100,
        step: int = 1,
        value: int | None = None,
        show_value: bool = False,
    ) -> None:
        if minimum >= maximum:
            raise ValueError("range minimum must be less than maximum")
        if step <= 0:
            raise ValueError("range step must be positive")
        if (maximum - minimum) % step:
            raise ValueError("range step must divide the declared bounds")
        self.minimum = minimum
        self.maximum = maximum
        self.step = step
        self.show_value = show_value
        self._emit_changes = False
        self._dragging = False
        super().__init__()
        self.set_reactive(RangeControl.value, minimum if value is None else value)
        self._emit_changes = True

    def _validate_value(self, value: int) -> int:
        if not isinstance(value, int):
            raise ValueError("range value must be an integer")
        if not self.minimum <= value <= self.maximum:
            raise ValueError("range value must be within its declared bounds")
        if (value - self.minimum) % self.step:
            raise ValueError("range value must align to its declared step")
        return value

    def watch_value(self, value: int) -> None:
        self.refresh()
        if self._emit_changes:
            self.post_message(self.Changed(self, value))

    def action_decrease(self) -> None:
        if not self.disabled:
            self.value = max(self.minimum, self.value - self.step)

    def action_increase(self) -> None:
        if not self.disabled:
            self.value = min(self.maximum, self.value + self.step)

    def action_minimum(self) -> None:
        if not self.disabled:
            self.value = self.minimum

    def action_maximum(self) -> None:
        if not self.disabled:
            self.value = self.maximum

    def _set_from_x(self, x: int) -> None:
        if self.disabled:
            return
        track_width = self._track_width
        position = max(0, min(track_width - 1, x))
        steps = (self.maximum - self.minimum) // self.step
        index = round(position * steps / max(track_width - 1, 1))
        self.value = self.minimum + index * self.step

    def on_mouse_down(self, event: MouseDown) -> None:
        if event.button == 1:
            self._dragging = True
            self.capture_mouse()
            self._set_from_x(event.x)
            event.stop()

    def on_mouse_move(self, event: MouseMove) -> None:
        if self._dragging:
            self._set_from_x(event.x)
            event.stop()

    def on_mouse_up(self, event: MouseUp) -> None:
        if self._dragging:
            self._dragging = False
            self.release_mouse()
            event.stop()

    def on_click(self, event: Click) -> None:
        self._set_from_x(event.x)
        event.stop()

    @property
    def _track_width(self) -> int:
        value_width = len(str(self.maximum)) + 1 if self.show_value else 0
        return max(1, self.content_size.width - value_width)

    def render(self) -> Text:
        track_width = self._track_width
        progress = (self.value - self.minimum) / (self.maximum - self.minimum)
        thumb = round(progress * (track_width - 1))
        rendered = Text()
        if thumb:
            rendered.append("━" * thumb, self.get_component_rich_style("range--filled"))
        rendered.append("●", self.get_component_rich_style("range--thumb"))
        if thumb + 1 < track_width:
            rendered.append("─" * (track_width - thumb - 1), self.get_component_rich_style("range--track"))
        if self.show_value:
            rendered.append(f" {self.value}", self.get_component_rich_style("range--value"))
        return rendered
