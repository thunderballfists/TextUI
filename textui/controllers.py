"""Per-App Python controller loading and explicit action exports."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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
from .timers import RuntimeTimers


def action(function: Callable[..., Any]) -> Callable[..., Any]:
    """Expose a linked controller function to document event directives."""
    function.__textui_action__ = True
    return function


@dataclass(frozen=True, slots=True)
class Command:
    """Metadata for one linked-script operation exposed to project UI."""

    name: str
    label: str
    shortcut: str | None
    description: str
    enabled: bool


@dataclass(frozen=True, slots=True)
class _CommandOptions:
    label: str | None
    shortcut: str | None
    description: str | None
    enabled: bool


def command(
    *,
    label: str | None = None,
    shortcut: str | None = None,
    description: str | None = None,
    enabled: bool = True,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Expose a zero-argument linked-script function as a shared command."""

    options = _CommandOptions(label, shortcut, description, enabled)

    def decorate(function: Callable[..., Any]) -> Callable[..., Any]:
        function.__textui_command__ = options
        function.__textui_action__ = True
        return function

    return decorate


def _arity(function: Callable[..., Any], allowed: set[int], location: SourceLocation) -> int:
    parameters = tuple(signature(function).parameters.values())
    if any(p.kind not in {Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD} or p.default is not Parameter.empty for p in parameters):
        raise DocumentValidationError(f"unsupported signature for {function.__name__}", location=location)
    if len(parameters) not in allowed:
        raise DocumentValidationError(f"unsupported signature for {function.__name__}", location=location)
    return len(parameters)


def _command_metadata(name: str, options: _CommandOptions, location: SourceLocation) -> Command:
    for field, value in (("label", options.label), ("shortcut", options.shortcut), ("description", options.description)):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise DocumentValidationError(f"command {field} must be a non-empty string", location=location)
    if not isinstance(options.enabled, bool):
        raise DocumentValidationError("command enabled must be a boolean", location=location)
    label = options.label or " ".join(part.capitalize() for part in name.strip("_").split("_"))
    return Command(name, label, options.shortcut, options.description or label, options.enabled)


class ProjectWindow:
    """A controller's App-scoped host facade."""

    def __init__(self, app: Any, registry: ComponentRegistry) -> None:
        self.app = app
        self.registry = registry
        self._document: BoundDocument | None = None
        self.phase = "created"
        self.timers = RuntimeTimers(app, self)

    @property
    def document(self) -> BoundDocument:
        if self._document is None:
            raise DocumentStateError("window.document is available after document binding")
        return self._document

    def after(self, seconds: float, callback: Callable[[], Any]):
        return self.timers.schedule(seconds, callback, repeat=False)

    def every(self, seconds: float, callback: Callable[[], Any], *, thread: bool = False):
        return self.timers.schedule(seconds, callback, repeat=True, thread=thread)

    def call_ui(self, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        if self.phase != "ready":
            raise DocumentStateError("window.call_ui is available only while ready")
        return self.app.call_from_thread(callback, *args, **kwargs)


class ControllerSet:
    def __init__(self, window: ProjectWindow) -> None:
        self.window = window
        self.actions: dict[str, Callable[[ActionContext], Any]] = {}
        self.commands: dict[str, Command] = {}
        self.command_callbacks: dict[str, Callable[[], Any]] = {}
        self.command_locations: dict[str, SourceLocation] = {}
        self.hooks: dict[str, tuple[Callable[..., Any], SourceLocation]] = {}
        self.periodic: list[tuple[float, Callable[[], Any], bool]] = []

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
            command_options = getattr(value, "__textui_command__", None) if callable(value) else None
            if command_options is not None and getattr(value, "__module__", None) == module.__name__:
                if name in self.actions:
                    raise DocumentValidationError(f"duplicate action {name!r}", location=location)
                if not isinstance(command_options, _CommandOptions):
                    raise DocumentValidationError(f"invalid command {name!r}", location=location)
                _arity(value, {0}, location)
                self.commands[name] = _command_metadata(name, command_options, location)
                self.command_callbacks[name] = value
                self.command_locations[name] = location
                self.actions[name] = lambda context, callback=value: callback()
            elif callable(value) and getattr(value, "__textui_action__", False) and getattr(value, "__module__", None) == module.__name__:
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
            if callable(value) and getattr(value, "__textui_every__", None) is not None and getattr(value, "__module__", None) == module.__name__:
                _arity(value, {0}, location)
                seconds, thread = value.__textui_every__
                self.periodic.append((seconds, value, thread))

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
