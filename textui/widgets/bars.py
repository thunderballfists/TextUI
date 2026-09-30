"""Three-slot header and status-bar layout primitives."""
from __future__ import annotations

from rich.style import Style
from rich.cells import split_graphemes
from rich.segment import Segment
from textual.geometry import Region
from textual.strip import Strip
from textual.containers import Horizontal
from textual.widgets import Label
from textual.color import Color

from ..styling import BackgroundGradient, GradientSlice
from ..registry import BuildContext, ComponentRegistry, ComponentSpec


class GradientLabel(Label):
    """A bar label that paints its glyph cells over the active gradient."""

    def render_lines(self, crop: Region) -> list[Strip]:
        """Paint native rendered cells, including alignment, wrapping and padding."""
        strips = super().render_lines(crop)
        if self.parent is None:
            return strips
        slot = self.parent
        bar = slot.parent
        if not isinstance(bar, SlotBar) or self.styles.background.a or slot.styles.background.a:
            return strips
        gradient = bar.active_background_gradient
        if gradient is None:
            return strips
        width, height = max(bar.content_size.width, 1), max(bar.content_size.height, 1)
        offset_x = self.region.x + crop.x - bar.content_region.x
        offset_y = self.region.y + crop.y - bar.content_region.y
        filters = self.get_line_filters()
        painted = []
        for row, strip in enumerate(strips):
            segments = []
            x = offset_x
            for segment in strip:
                spans, _ = split_graphemes(segment.text)
                for start, end, cells in spans:
                    color = gradient.color_at(x + .5, offset_y + row + .5, width, height)
                    swatch = Strip([Segment(" ", Style(bgcolor=color))])
                    for line_filter in filters:
                        swatch = swatch.apply_filter(line_filter, self.background_colors[1])
                    background = next(iter(swatch)).style.bgcolor
                    style = (segment.style or Style()) + Style(bgcolor=background)
                    segments.append(Segment(segment.text[start:end], style, segment.control))
                    x += cells
            painted.append(Strip(segments, strip.cell_length))
        return painted


class HeaderSlot(Horizontal):
    """One flexible region in a header-style bar."""

    def __init__(self, position: str, *children) -> None:
        super().__init__(*children)
        self.position = position
        self.has_content = bool(children)
        self.add_class(f"-{position}")

    def render(self) -> GradientSlice | str:
        """Supply this slot's clipped section of the bar background."""
        bar = self.parent
        if not isinstance(bar, SlotBar) or self.styles.background.a:
            return ""
        gradient = bar.active_background_gradient
        if gradient is None:
            return ""
        return GradientSlice(
            gradient,
            self.content_region.x - bar.content_region.x,
            self.content_region.y - bar.content_region.y,
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
    /* With nothing in the centre there is nothing to keep centred, so the right slot
       takes the room its content needs and the left slot keeps the rest. Left at 1fr
       it gets half the bar and clips controls that need more than that. */
    SlotBar.-no-center > HeaderSlot.-right {
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
        self._background_gradients: tuple[tuple[Color, BackgroundGradient], ...] = ()
        slots = {slot.position: slot for slot in declared_slots}
        self.slots = tuple(
            slots.get(position, HeaderSlot(position))
            for position in ("left", "center", "right")
        )
        super().__init__(*self.slots)
        if not self.slots[1].has_content:
            self.add_class("-no-center")

    @property
    def active_background_gradient(self) -> BackgroundGradient | None:
        """Use the gradient marker currently selected by native TCSS cascade."""
        background = self.styles.background
        for marker, gradient in self._background_gradients:
            if background == marker:
                return gradient
        return None

    def set_background_gradients(self, gradients: tuple[tuple[Color, BackgroundGradient], ...]) -> None:
        """Store candidates so live class and style changes select the winner."""
        self._background_gradients = gradients
        self.refresh()
        for slot in self.slots:
            slot.refresh()
            for child in slot.children:
                if isinstance(child, GradientLabel):
                    child.refresh()

    def render(self) -> BackgroundGradient | str:
        """Supply the active bar background to Textual's native renderer."""
        return self.active_background_gradient or ""


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
