"""Three-slot header and status-bar layout primitives."""
from __future__ import annotations

from rich.style import Style
from rich.text import Text
from textual.containers import Horizontal
from textual.widgets import Label
from textual.renderables.gradient import LinearGradient

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
        width = max(self.parent.content_size.width, 1)
        offset = self.region.x - self.parent.region.x
        for index in range(len(content)):
            color = gradient._color_gradient.get_rich_color((offset + index + .5) / width)
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
        """Render a bar gradient beneath this slot's child controls."""
        self._background_gradient = gradient
        for child in self.children:
            if isinstance(child, GradientLabel):
                child.set_background_gradient(gradient)
        self.refresh()

    def render(self) -> LinearGradient | str:
        """Supply the optional slot background to Textual's native renderer."""
        return self._background_gradient or ""


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
