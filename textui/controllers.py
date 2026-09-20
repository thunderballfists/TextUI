"""Per-App Python controller loading and explicit action exports."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from inspect import Parameter, isawaitable, signature
from pathlib import Path
from string import printable
from types import ModuleType
from typing import Any
from uuid import uuid4
import sys

from textual.binding import Binding
from textual.keys import Keys

from .actions import ActionContext, ActionOptions
from .document import BoundDocument
from .errors import DocumentStateError, DocumentValidationError, SourceLocation, TextUIError
from .registry import ComponentRegistry
from .timers import RuntimeTimers


def action(function: Callable[..., Any] | None = None, *, target: str | None = None, supersede: bool = False):
    """Expose a linked controller function to document event directives."""
    options = ActionOptions(target, supersede)
    def decorate(callback: Callable[..., Any]) -> Callable[..., Any]:
        callback.__textui_action__ = options
        return callback
    return decorate(function) if function is not None else decorate


@dataclass(frozen=True, slots=True)
class Command:
    """Metadata for one linked-script operation exposed to project UI."""

    name: str
    label: str
    shortcut: str | None
    description: str
    enabled: bool
    target: str | None
    supersede: bool


@dataclass(frozen=True, slots=True)
class _CommandOptions:
    label: str | None
    shortcut: str | None
    description: str | None
    enabled: bool
    target: str | None
    supersede: bool


def command(
    *,
    label: str | None = None,
    shortcut: str | None = None,
    description: str | None = None,
    enabled: bool = True,
    target: str | None = None,
    supersede: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Expose a zero-argument linked-script function as a shared command."""

    options = _CommandOptions(label, shortcut, description, enabled, target, supersede)

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


def _normalize_shortcut(value: str) -> str:
    binding = next(iter(Binding.make_bindings([Binding(value, "textui_noop")])))
    return binding.key


_TEXTUAL_SHORTCUTS = {key.value for key in Keys}
_PRINTABLE_SHORTCUTS = {
    _normalize_shortcut(value)
    for value in printable
    if value.isprintable() and not value.isspace() and value != ","
}


def _shortcut(value: str, location: SourceLocation) -> str:
    if "," in value:
        raise DocumentValidationError("command shortcut must name one Textual key", location=location)
    try:
        value = _normalize_shortcut(value)
    except Exception as error:
        raise DocumentValidationError(f"command shortcut {value!r} is not a valid Textual key", location=location) from error
    if value not in _TEXTUAL_SHORTCUTS | _PRINTABLE_SHORTCUTS:
        raise DocumentValidationError(f"command shortcut {value!r} is not a valid Textual key", location=location)
    return value


def _command_metadata(name: str, options: _CommandOptions, location: SourceLocation) -> Command:
    for field, value in (("label", options.label), ("shortcut", options.shortcut), ("description", options.description)):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise DocumentValidationError(f"command {field} must be a non-empty string", location=location)
    if not isinstance(options.enabled, bool):
        raise DocumentValidationError("command enabled must be a boolean", location=location)
    label = options.label or " ".join(part.capitalize() for part in name.strip("_").split("_"))
    shortcut = _shortcut(options.shortcut, location) if options.shortcut is not None else None
    if options.target is not None and (not isinstance(options.target, str) or not options.target.isidentifier()):
        raise DocumentValidationError("command target must be an identifier", location=location)
    if not isinstance(options.supersede, bool):
        raise DocumentValidationError("command supersede must be a boolean", location=location)
    return Command(name, label, shortcut, options.description or label, options.enabled, options.target, options.supersede)


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
        self.action_metadata: dict[str, ActionOptions] = {}
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
                command = _command_metadata(name, command_options, location)
                if command.shortcut is not None and any(existing.shortcut == command.shortcut for existing in self.commands.values()):
                    raise DocumentValidationError(f"duplicate command shortcut {command.shortcut!r}", location=location)
                self.commands[name] = command
                self.command_callbacks[name] = value
                self.command_locations[name] = location
                self.actions[name] = lambda context, callback=value: callback()
                self.action_metadata[name] = ActionOptions(command.target, command.supersede)
            elif callable(value) and getattr(value, "__textui_action__", False) and getattr(value, "__module__", None) == module.__name__:
                if name in self.actions:
                    raise DocumentValidationError(f"duplicate action {name!r}", location=location)
                arity = _arity(value, {0, 1}, location)
                if arity == 0:
                    self.actions[name] = lambda context, callback=value: callback()
                else:
                    self.actions[name] = value
                options = getattr(value, "__textui_action__")
                if not isinstance(options, ActionOptions):
                    options = ActionOptions()
                if options.target is not None and (not isinstance(options.target, str) or not options.target.isidentifier()):
                    raise DocumentValidationError("action target must be an identifier", location=location)
                if not isinstance(options.supersede, bool):
                    raise DocumentValidationError("action supersede must be a boolean", location=location)
                self.action_metadata[name] = options
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
