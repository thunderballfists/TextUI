"""Public diagnostics for TextUI documents and runtime integration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceLocation:
    source: str
    line: int | None
    column: int | None = None
    tag: str | None = None

    def describe(self) -> str:
        position = self.source
        if self.line is not None:
            position += f":{self.line}"
        if self.tag is not None:
            position += f" <{self.tag}>"
        return position


class TextUIError(Exception):
    """Base class for every public TextUI error."""

    def __init__(self, message: str, *, location: SourceLocation | None = None, attribute: str | None = None, value: object | None = None) -> None:
        self.message = message
        self.location = location
        self.attribute = attribute
        self.value = value
        context = location.describe() if location else None
        if attribute:
            context = f"{context or 'document'} attribute {attribute!r}"
        super().__init__(f"{context}: {message}" if context else message)


class DocumentLoadError(TextUIError): pass
class DocumentSyntaxError(DocumentLoadError): pass
class DocumentValidationError(DocumentLoadError): pass
class DocumentStyleError(TextUIError): pass
class ComponentBuildError(TextUIError): pass
class DocumentStateError(TextUIError): pass
class ElementNotFoundError(TextUIError): pass
class ActionExecutionError(TextUIError): pass
class RegistryError(TextUIError): pass
