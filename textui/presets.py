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
"""

FOCUS_TCSS = """
Button:focus, Input:focus, Select:focus, TextArea:focus, Checkbox:focus,
Switch:focus, RadioButton:focus, RadioSet:focus, DataTable:focus,
Tree:focus, RuntimeList:focus {
    outline: solid $accent;
}
"""

# Structural defaults for an application shell. ``split`` already fills its parent;
# ``tabbed-content`` did not, so a vertical shell of header / tabbed-content / status-bar
# gave the tabs the whole screen and pushed the status bar off the bottom, and a
# ``1fr`` widget inside a pane collapsed because Textual sizes TabbedContent,
# its ContentSwitcher and each TabPane to their content. Any of these can still be
# overridden by an application's own TCSS.
LAYOUT_TCSS = """
TabbedContent {
    height: 1fr;
}
TabbedContent > ContentSwitcher {
    height: 1fr;
}
TabbedContent TabPane {
    height: 1fr;
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
