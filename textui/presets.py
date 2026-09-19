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


STYLE_PRESETS = {"compact": COMPACT_TCSS}


def style_preset(name: str) -> str:
    """Return a built-in stylesheet or reject an unknown preset name."""
    try:
        return STYLE_PRESETS[name]
    except KeyError as error:
        raise ValueError(f"unknown style preset {name!r}") from error
