"""Validate declarative project structure without executing project Python."""
from __future__ import annotations

from pathlib import Path

from .content import NativeChildren
from .document import Document
from .errors import DocumentValidationError, TextUIError
from .project import ProjectSource
from .widgets.builtin_widgets import default_component_registry
from .widgets.navigation import NavItem
from .widgets.split import Pane
from .widgets.structure import walk


# These canonical registrations have known native output types. Do not guess
# about controller-provided registrations or call factories to discover types.
_NATIVE_TAGS = {Pane: "pane", NavItem: "nav-item"}


def check_static(path: str | Path) -> Document:
    """Check built-ins, includes and reusable components; never bind or build."""
    document = ProjectSource.discover(path).lower(default_component_registry())
    for node in walk(document.nodes):
        for rule in node.spec.content.rules:
            if not isinstance(rule, NativeChildren):
                continue
            tag = _NATIVE_TAGS[rule.widget_type]
            count = len(node.children)
            if (count < rule.minimum or rule.maximum is not None and count > rule.maximum
                    or any(child.spec.tag != tag for child in node.children)):
                raise DocumentValidationError(rule.message, location=node.location)
    return document


def diagnostic(error: TextUIError, path: str | Path) -> dict[str, object]:
    """Return one contextual error record suitable for editor integrations."""
    location = error.location
    return {
        "file": location.source if location else str(Path(path).resolve()),
        "line": location.line if location else None,
        "column": location.column if location else None,
        "element": location.tag if location else None,
        "attribute": error.attribute,
        "message": error.message,
    }
