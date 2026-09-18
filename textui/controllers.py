"""Per-App Python controller loading and explicit action exports."""
from __future__ import annotations

from collections.abc import Callable
from inspect import Parameter, isawaitable, signature
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import uuid4
import sys

from .actions import ActionContext
from .document import BoundDocument
from .errors import DocumentStateError, DocumentValidationError, SourceLocation, TextUIError
from .registry import ComponentRegistry


def action(function: Callable[..., Any]) -> Callable[..., Any]:
    """Expose a linked controller function to document event directives."""
    function.__textui_action__ = True
    return function


def _arity(function: Callable[..., Any], allowed: set[int], location: SourceLocation) -> int:
    parameters = tuple(signature(function).parameters.values())
    if any(p.kind not in {Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD} or p.default is not Parameter.empty for p in parameters):
        raise DocumentValidationError(f"unsupported signature for {function.__name__}", location=location)
    if len(parameters) not in allowed:
        raise DocumentValidationError(f"unsupported signature for {function.__name__}", location=location)
    return len(parameters)


class ProjectWindow:
    """A controller's App-scoped host facade."""

    def __init__(self, app: Any, registry: ComponentRegistry) -> None:
        self.app = app
        self.registry = registry
        self._document: BoundDocument | None = None
        self.phase = "created"

    @property
    def document(self) -> BoundDocument:
        if self._document is None:
            raise DocumentStateError("window.document is available after document binding")
        return self._document


class ControllerSet:
    def __init__(self, window: ProjectWindow) -> None:
        self.window = window
        self.actions: dict[str, Callable[[ActionContext], Any]] = {}
        self.hooks: dict[str, tuple[Callable[..., Any], SourceLocation]] = {}

    def load(self, path: Path) -> None:
        location = SourceLocation(str(path), 1, tag="script")
        name = f"_textui_controller_{uuid4().hex}"
        module = ModuleType(name)
        module.__file__ = str(path)
        module.__dict__["window"] = self.window
        try:
            source = path.read_text(encoding="utf-8")
            sys.modules[name] = module
            try:
                exec(compile(source, str(path), "exec"), module.__dict__)
            finally:
                sys.modules.pop(name, None)
        except Exception as error:
            raise TextUIError(f"script failed: {error}", location=location) from error
        for name, value in module.__dict__.items():
            if callable(value) and getattr(value, "__textui_action__", False) and getattr(value, "__module__", None) == module.__name__:
                if name in self.actions:
                    raise DocumentValidationError(f"duplicate action {name!r}", location=location)
                arity = _arity(value, {0, 1}, location)
                if arity == 0:
                    self.actions[name] = lambda context, callback=value: callback()
                else:
                    self.actions[name] = value
            if name in {"on_setup", "on_ready", "on_close"} and callable(value) and getattr(value, "__module__", None) == module.__name__:
                if name in self.hooks:
                    raise DocumentValidationError(f"duplicate hook {name!r}", location=location)
                _arity(value, {0}, location)
                self.hooks[name] = (value, location)

    async def hook(self, name: str) -> None:
        if name not in self.hooks:
            return
        callback, location = self.hooks[name]
        try:
            result = callback()
            if isawaitable(result):
                await result
        except Exception as error:
            raise TextUIError(f"{name} failed: {error}", location=location) from error
