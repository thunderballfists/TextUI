"""Deterministic authoring artifacts derived from the built-in registry."""
from __future__ import annotations

import json
from pathlib import Path

from ..widgets.builtin_widgets import default_component_registry
from .completion import completion_data
from .reference import llm_reference, markup_reference
from .schema import schema


def artifacts() -> dict[str, str]:
    """Generate fresh artifacts without invoking converters or factories."""
    description = default_component_registry().describe()
    html, web = completion_data(description)
    return {
        "docs/markup-reference.md": markup_reference(description),
        "spec/textui.xsd": schema(description),
        "spec/textui-authoring.xsd": schema(description, authoring=True),
        "spec/vscode-html-custom-data.json": json.dumps(html, indent=2, ensure_ascii=False) + "\n",
        "spec/web-types.json": json.dumps(web, indent=2, ensure_ascii=False) + "\n",
        "docs/llm-reference.md": llm_reference(description),
        "llms.txt": (
            "# TextUI\n\n"
            "> Declarative, HTML-like markup for native Textual applications.\n\n"
            "TextUI uses strict XML syntax, TCSS styles and trusted Python controllers. "
            "Install textui-markup; import textui. HTML completion data is not an HTML grammar.\n\n"
            "## Authoring\n\n"
            "- [LLM reference](https://github.com/thunderballfists/TextUI/blob/main/docs/llm-reference.md): "
            "Self-contained grammar, examples and common mistakes.\n"
            "- [Markup reference](https://github.com/thunderballfists/TextUI/blob/main/docs/markup-reference.md): "
            "Generated attributes, events, defaults and rules.\n"
            "- [Editor guide](https://github.com/thunderballfists/TextUI/blob/main/docs/editors.md): "
            "Schema profiles, completions and static checking.\n\n"
            "## Runtime\n\n"
            "- [Project runtime](https://github.com/thunderballfists/TextUI/blob/main/docs/project-runtime.md): "
            "Controllers, actions, components, lifecycle and timers.\n"
            "- [Examples](https://github.com/thunderballfists/TextUI/tree/main/examples): Runnable projects.\n"
        ),
    }


def write_spec(output: str | Path) -> tuple[Path, ...]:
    """Write the generated reference tree to an explicitly selected directory."""
    root = Path(output)
    written = []
    for relative, content in artifacts().items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        written.append(target)
    return tuple(written)
