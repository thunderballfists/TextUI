"""Three-slot header and status-bar layout primitives."""
from __future__ import annotations

from textual.containers import Horizontal

from ..registry import BuildContext, ComponentRegistry, ComponentSpec


class HeaderSlot(Horizontal):
    """One flexible region in a header-style bar."""

    def __init__(self, position: str, *children) -> None:
        super().__init__(*children)
        self.position = position
        self.has_content = bool(children)
        self.add_class(f"-{position}")


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
    """

    def __init__(self, *declared_slots: HeaderSlot) -> None:
        slots = {slot.position: slot for slot in declared_slots}
        self.slots = tuple(
            slots.get(position, HeaderSlot(position))
            for position in ("left", "center", "right")
        )
        super().__init__(*self.slots)
        if not self.slots[1].has_content:
            self.add_class("-no-center")


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
