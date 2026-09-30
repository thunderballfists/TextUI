"""Three-slot header and status-bar layout primitives."""
from __future__ import annotations

from rich.style import Style
from rich.text import Text
from textual.containers import Horizontal
from textual.widgets import Label
from textual.renderables.gradient import LinearGradient

from ..styling import BackgroundGradient, GradientSlice
from ..registry import BuildContext, ComponentRegistry, ComponentSpec


class GradientLabel(Label):
    """A bar label that paints its glyph cells over the active gradient."""

    def __init__(self, *args, **kwargs) -> None:
        self._textui_gradient: LinearGradient | None = None
        super().__init__(*args, **kwargs)

    def set_background_gradient(self, gradient: LinearGradient | None) -> None:
        self._textui_gradient = gradient
        self.refresh()

    def render(self):
        gradient = self._textui_gradient
        if gradient is None or self.parent is None:
            return super().render()
        content = getattr(self.content, "plain", str(self.content))
        rendered = Text(content)
        if not isinstance(gradient, BackgroundGradient):
            return super().render()
        bar = self.parent.parent
        if not isinstance(bar, SlotBar):
            return super().render()
        width = max(bar.content_size.width, 1)
        height = max(bar.content_size.height, 1)
        offset_x = self.region.x - bar.region.x
        offset_y = self.region.y - bar.region.y
        for index in range(len(content)):
            color = gradient.color_at(offset_x + index + .5, offset_y + .5, width, height)
            rendered.stylize(Style(bgcolor=color), index, index + 1)
        return rendered


class HeaderSlot(Horizontal):
    """One flexible region in a header-style bar."""

    def __init__(self, position: str, *children) -> None:
        self._background_gradient: LinearGradient | None = None
        super().__init__(*children)
        self.position = position
        self.add_class(f"-{position}")

    def set_background_gradient(self, gradient: LinearGradient | None) -> None:
        """Pass the bar gradient to labels and preserve its full-bar coordinates."""
        self._background_gradient = gradient
        for child in self.children:
            if isinstance(child, GradientLabel):
                child.set_background_gradient(gradient)
        self.refresh()

    def render(self) -> GradientSlice | str:
        """Supply this slot's clipped section of the bar background."""
        gradient = self._background_gradient
        bar = self.parent
        if not isinstance(gradient, BackgroundGradient) or not isinstance(bar, SlotBar):
            return ""
        return GradientSlice(
            gradient,
            self.region.x - bar.region.x,
            self.region.y - bar.region.y,
            max(bar.content_size.width, 1),
            max(bar.content_size.height, 1),
        )


class SlotBar(Horizontal):
    """A three-slot horizontal bar with a centered middle region."""

    DEFAULT_CSS = """
    SlotBar {
        width: 100%;
        height: auto;
    }
    SlotBar > HeaderSlot {
        width: 1fr;
        height: auto;
        background: transparent;
    }
    SlotBar > HeaderSlot.-center {
        width: auto;
    }
    SlotBar > HeaderSlot.-right {
        align: right middle;
    }
    SlotBar Label {
        background: transparent;
    }
    """

    def __init__(self, *declared_slots: HeaderSlot) -> None:
        self._background_gradient: LinearGradient | None = None
        slots = {slot.position: slot for slot in declared_slots}
        self.slots = tuple(
            slots.get(position, HeaderSlot(position))
            for position in ("left", "center", "right")
        )
        super().__init__(*self.slots)

    def set_background_gradient(self, gradient: LinearGradient | None) -> None:
        """Render a TCSS gradient beneath the bar's child widgets."""
        self._background_gradient = gradient
        for slot in self.slots:
            slot.set_background_gradient(gradient)
        self.refresh()

    def render(self) -> LinearGradient | str:
        """Supply the optional bar background to Textual's native renderer."""
        return self._background_gradient or ""


def _slot(position: str):
    def build(context: BuildContext) -> HeaderSlot:
        return HeaderSlot(position, *context.children)
    return build


SLOT_FACTORIES = {position: _slot(position) for position in ("left", "center", "right")}


def build_bar(context: BuildContext) -> SlotBar:
    if any(not isinstance(child, HeaderSlot) for child in context.children):
        raise ValueError("header accepts left, center, and right slots")
    if len({child.position for child in context.children}) != len(context.children):
        raise ValueError("header accepts each slot at most once")
    return SlotBar(*context.children)


def register_bars(registry: ComponentRegistry) -> None:
    for position in ("left", "center", "right"):
        registry.register(ComponentSpec(
            tag=position,
            factory=SLOT_FACTORIES[position],
            child_policy="widgets",
        ))
    for tag in ("header", "status-bar"):
        registry.register(ComponentSpec(tag=tag, factory=build_bar, child_policy="widgets"))
