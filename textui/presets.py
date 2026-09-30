"""Built-in opt-in TCSS presets."""
from __future__ import annotations


COMPACT_TCSS = """
Button {
    min-height: 1;
    padding: 0 1;
}
Input, Select, TextArea {
    padding: 0 1;
}
Checkbox, Switch, RadioButton {
    padding: 0;
}
/* Compact controls have no border rows to spare for an outline. Keep native
   focus styles and tint editable controls without covering their content. */
Button:focus, Checkbox:focus, Switch:focus, RadioButton:focus, RadioSet:focus {
    outline: none;
}
Input:focus, Select:focus, TextArea:focus {
    outline: none;
    background: $accent 25%;
}
"""

FOCUS_TCSS = """
Button:focus, Input:focus, Select:focus, TextArea:focus, Checkbox:focus,
Switch:focus, RadioButton:focus, RadioSet:focus, DataTable:focus,
Tree:focus, RuntimeList:focus {
    background: $accent 15%;
}
"""

BUTTON_BORDERS_TCSS = """
Button {
    border: round $primary !important;
}
Button:hover {
    border: round $accent !important;
}
Button:focus {
    border: double $primary !important;
}
"""

STYLE_PRESETS = {"compact": COMPACT_TCSS, "borders": BUTTON_BORDERS_TCSS}


def style_preset(name: str) -> str:
    """Return a built-in stylesheet or reject an unknown preset name."""
    try:
        return STYLE_PRESETS[name]
    except KeyError as error:
        raise ValueError(f"unknown style preset {name!r}") from error
