"""The strict, typed TextUI document definition API."""

from .document import Document
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
    "ActionExecutionError",
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
    "TextUIError",
    "UNSET",
    "boolean",
    "enum",
    "integer",
]
