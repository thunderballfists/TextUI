"""The strict, typed TextUI document definition API."""

from .actions import ActionCallback, ActionContext
from .document import BoundDocument, Document
from .textui import TextUI
from .controllers import action
from .timers import every
from .errors import (
    ActionExecutionError,
    ComponentBuildError,
    DocumentLoadError,
    DocumentStateError,
    DocumentStyleError,
    DocumentSyntaxError,
    DocumentValidationError,
    ElementNotFoundError,
    RegistryError,
    SourceLocation,
    TextUIError,
)
from .loader import DocumentLoader
from .nodes import ElementNode, StyleBlock
from .registry import (
    AttributeSpec,
    BuildContext,
    ComponentRegistry,
    ComponentSpec,
    EventSpec,
    UNSET,
    boolean,
    enum,
    integer,
)

__all__ = [
    "ActionCallback",
    "ActionContext",
    "ActionExecutionError",
    "BoundDocument",
    "AttributeSpec",
    "BuildContext",
    "ComponentBuildError",
    "ComponentRegistry",
    "ComponentSpec",
    "Document",
    "DocumentLoadError",
    "DocumentLoader",
    "DocumentStateError",
    "DocumentStyleError",
    "DocumentSyntaxError",
    "DocumentValidationError",
    "ElementNode",
    "ElementNotFoundError",
    "EventSpec",
    "RegistryError",
    "SourceLocation",
    "StyleBlock",
    "TextUI",
    "TextUIError",
    "UNSET",
    "boolean",
    "enum",
    "integer",
    "action",
    "every",
]
