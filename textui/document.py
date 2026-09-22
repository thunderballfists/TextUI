"""Immutable document definitions and single-use native runtime bindings."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from inspect import isawaitable
from types import MappingProxyType
from weakref import WeakSet

from textual.app import App
from textual.content import Content
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Checkbox, Input, RadioButton, RadioSet, Select, Switch, TextArea

from .actions import ActionCallback, ActionContext, ActionInvocation
from .errors import (
    ActionExecutionError, ComponentBuildError, DocumentStateError,
    DocumentValidationError, ElementNotFoundError,
)
from .nodes import ElementNode, StyleBlock
from .registry import BuildContext, EventSpec
from .widgets.modal import MarkupModal, build_modal
from .styling import apply_inline, commit_styles, prepare_styles, prepare_styles_from

# A factory may not recycle an instance across bindings, even before mounting.
_built_widgets: WeakSet[Widget] = WeakSet()
COMPACT_WIDGET_TYPES = (Button, Checkbox, Input, RadioButton, RadioSet, Select, Switch, TextArea)


class ModalResult(asyncio.Future[object | None]):
    """A modal dismissal future with a separate awaitable for its initial mount."""

    mounted: Awaitable[object]


def _walk(nodes: tuple[ElementNode, ...]) -> Iterable[ElementNode]:
    for node in nodes:
        yield node
        yield from _walk(node.children)


@dataclass(frozen=True, slots=True)
class Document:
    nodes: tuple[ElementNode, ...]
    styles: tuple[StyleBlock, ...]
    source_name: str

    def __post_init__(self) -> None:
        object.__setattr__(self, 'nodes', tuple(self.nodes))
        object.__setattr__(self, 'styles', tuple(self.styles))

    def bind(
        self,
        app: App,
        *,
        actions: Mapping[str, ActionCallback],
        action_metadata: Mapping[str, object] | None = None,
        commands: Mapping[str, object] | None = None,
        command_callbacks: Mapping[str, Callable[[], object]] | None = None,
        command_locations: Mapping[str, object] | None = None,
    ) -> BoundDocument:
        """Validate callbacks and reserve one binding on an initialized App."""
        if not isinstance(app, App) or not hasattr(app, 'stylesheet'):
            raise DocumentStateError('Bind to an initialized Textual App')
        if app.is_running and not getattr(app, "_textui_loading", False):
            raise DocumentStateError('Bind the document before running the App')
        if hasattr(app, '_textui_document_binding'):
            raise DocumentStateError('An App may have only one document binding')
        callbacks = dict(actions)
        metadata = dict(action_metadata or {})
        declared_ids = {node.common['id'] for node in _walk(self.nodes) if node.common['id'] is not None and not node.private_id}
        for name, options in metadata.items():
            target = getattr(options, "target", None)
            if target is not None and target not in declared_ids:
                raise DocumentValidationError(f"Action {name!r} target {target!r} must name a declared ID")
        declared_commands = dict(commands or {})
        callbacks_by_command = dict(command_callbacks or {})
        locations_by_command = dict(command_locations or {})
        for node in _walk(self.nodes):
            if node.spec.tag == "command-button":
                command_name = node.attributes["command"]
                if command_name not in declared_commands:
                    raise DocumentValidationError(f"Command {command_name!r} must be declared", location=node.location, attribute="command", value=command_name)
                if command_name not in callbacks_by_command or not callable(callbacks_by_command[command_name]):
                    raise DocumentValidationError(f"Command {command_name!r} must expose a callable", location=node.location, attribute="command", value=command_name)
            for event_name, name in node.events.items():
                if name not in callbacks or not callable(callbacks[name]):
                    raise DocumentValidationError(f'Action {name!r} must be exposed as a callable', location=node.location, attribute=f'on-{event_name}', value=name)
        for name, callback in callbacks.items():
            if not isinstance(name, str) or not name.isidentifier() or not callable(callback):
                raise DocumentValidationError(f'Action {name!r} must have an identifier name and a callable value')
        bound = BoundDocument(self, app, callbacks, metadata, declared_commands, callbacks_by_command, locations_by_command)
        app._textui_document_binding = bound
        return bound


class BoundDocument:
    """One App's callbacks, constructed tree, and native message bindings."""

    def __init__(
        self,
        definition: Document,
        app: App,
        actions: Mapping[str, ActionCallback],
        action_metadata: Mapping[str, object],
        commands: Mapping[str, object],
        command_callbacks: Mapping[str, Callable[[], object]],
        command_locations: Mapping[str, object],
    ) -> None:
        self.definition = definition
        self.app = app
        self.actions = MappingProxyType(dict(actions))
        self.action_metadata = MappingProxyType(dict(action_metadata))
        self.commands = MappingProxyType(dict(commands))
        self._command_callbacks = MappingProxyType(dict(command_callbacks))
        self._command_locations = MappingProxyType(dict(command_locations))
        self._state = 'bound'
        self._declared_ids = {node.common['id']: node.location for node in _walk(definition.nodes) if node.common['id'] is not None and not node.private_id}
        self._widgets: dict[str, Widget] = {}
        self._bindings: dict[type, list[tuple[Widget, EventSpec, str, ElementNode]]] = {}
        self._action_tasks: set[asyncio.Future[object]] = set()
        self._lifecycle_tasks: dict[tuple[str, str], set[asyncio.Future[object]]] = {}
        self._lifecycle_invocations: dict[asyncio.Future[object], ActionInvocation] = {}
        self._modal_nodes = {
            node.common["id"]: node
            for node in definition.nodes
            if node.spec.factory is build_modal and node.common["id"] is not None
        }
        self._active_modal_ids: set[str] = set()
        self._preset_enabled = {block.preset: True for block in definition.styles if block.preset is not None}
        self._compact_widgets: list[Widget] = []
        self._autofocus_widgets: list[Widget] = []

    def _apply_compact_preset(self, widget: Widget) -> None:
        """Use Textual's native compact state for controls that support it."""
        if "compact" in self._preset_enabled and isinstance(widget, COMPACT_WIDGET_TYPES):
            self._compact_widgets.append(widget)
            widget.compact = self._preset_enabled["compact"]

    def _set_compact_preset(self, enabled: bool) -> None:
        for widget in self._compact_widgets:
            widget.compact = enabled

    def _build_node(
        self,
        node: ElementNode,
        widgets: dict[str, Widget],
        bindings: dict[type, list[tuple[Widget, EventSpec, str, ElementNode]]],
    ) -> Widget:
        children = tuple(self._build_node(child, widgets, bindings) for child in node.children)
        try:
            widget = node.spec.factory(BuildContext(node.attributes, node.text, children, node.location))
            if not isinstance(widget, Widget):
                raise TypeError('Component factory must return a fresh Widget')
            if widget in _built_widgets:
                raise ValueError('Component factory reused a Widget; return a fresh instance')
            if widget.parent is not None or widget.is_mounted:
                raise ValueError('Component factory must return a fresh, unmounted Widget without a parent')
            _built_widgets.add(widget)
            if node.common['id'] is not None:
                widget.id = node.common['id']
            widget.add_class(*node.common['classes'])
            widget.disabled = node.common['disabled']
            if node.common['autofocus']:
                if not widget.can_focus:
                    raise ValueError('autofocus requires a focusable widget')
                widget._textui_autofocus = True
                self._autofocus_widgets.append(widget)
            self._apply_compact_preset(widget)
            command_name = getattr(widget, "_textui_command_name", None)
            if command_name is not None:
                command = self.commands[command_name]
                widget.label = Content(command.label)
                widget.disabled = widget.disabled or not command.enabled
        except Exception as error:
            raise ComponentBuildError(str(error), location=node.location) from error
        if node.common['style'] is not None:
            apply_inline(widget, node.common['style'], node.location)
        if node.common['id'] is not None and not node.private_id:
            widgets[node.common['id']] = widget
        for event_name, action in node.events.items():
            event = node.spec.events[event_name]
            bindings.setdefault(event.message_type, []).append((widget, event, action, node))
        command_name = getattr(widget, "_textui_command_name", None)
        if command_name is not None:
            bindings.setdefault(Button.Pressed, []).append((
                widget,
                EventSpec(Button.Pressed, lambda event: event.button),
                command_name,
                node,
            ))
        return widget

    def compose(self) -> Iterable[Widget]:
        """Prepare atomically before returning roots; a binding is single-use."""
        if self._state != 'bound':
            raise DocumentStateError(f'Document composition is single-use (state: {self._state})')
        self._state = 'preparing'
        widgets: dict[str, Widget] = {}
        bindings: dict[type, list[tuple[Widget, EventSpec, str, ElementNode]]] = {}

        try:
            staged = prepare_styles(self.app, self.definition.styles)
            roots = tuple(self._build_node(node, widgets, bindings) for node in self.definition.nodes if node.spec.factory is not build_modal)
            commit_styles(self.app, staged)
        except BaseException:
            self._state = 'failed'
            raise
        self._widgets, self._bindings = widgets, bindings
        self._state = 'prepared'
        self.app.call_after_refresh(self._focus_autofocus)
        return iter(roots)

    def _focus_autofocus(self) -> None:
        self._focus_widgets(self._autofocus_widgets)

    @staticmethod
    def _focus_widgets(widgets: Iterable[Widget]) -> None:
        for widget in reversed(tuple(widgets)):
            if widget.is_mounted and widget.display:
                widget.focus()
                return

    def toggle_style_preset(self, name: str) -> bool:
        """Toggle a declared style preset and return whether it is now enabled."""
        if name not in self._preset_enabled or self._state != 'prepared':
            raise DocumentStateError(f"No declared style preset {name!r}")

        enabled = not self._preset_enabled[name]
        blocks = tuple(
            block
            for block in self.definition.styles
            if block.preset is None
            or (block.preset == name and enabled)
            or (block.preset != name and self._preset_enabled[block.preset])
        )
        staged = prepare_styles_from(self.app.stylesheet, blocks, replace=self.definition.styles)
        commit_styles(self.app, staged)
        self._preset_enabled[name] = enabled
        if name == "compact":
            self._set_compact_preset(enabled)
        self.app.refresh_css(animate=False)
        return enabled

    def push_modal(self, modal_id: str):
        """Push a declared modal and return a future resolved by dismissal."""
        node = self._modal_nodes.get(modal_id)
        if node is None:
            raise ElementNotFoundError(f'No declared modal has ID {modal_id!r}')
        if modal_id in self._active_modal_ids:
            raise DocumentStateError(f'Modal {modal_id!r} is already active')
        widgets: dict[str, Widget] = {}
        bindings: dict[type, list[tuple[Widget, EventSpec, str, ElementNode]]] = {}
        compact_start = len(self._compact_widgets)
        try:
            modal = self._build_node(node, widgets, bindings)
        except BaseException:
            del self._compact_widgets[compact_start:]
            raise
        compact_widgets = tuple(self._compact_widgets[compact_start:])
        if not isinstance(modal, MarkupModal):
            del self._compact_widgets[compact_start:]
            raise DocumentStateError(f'Element {modal_id!r} is not a modal')
        future = ModalResult()
        owned_entries = {id(entry) for entries in bindings.values() for entry in entries}

        def remove_registrations() -> None:
            for element_id, widget in widgets.items():
                if self._widgets.get(element_id) is widget:
                    self._widgets.pop(element_id)
            for message_type in bindings:
                remaining = [entry for entry in self._bindings.get(message_type, ()) if id(entry) not in owned_entries]
                if remaining:
                    self._bindings[message_type] = remaining
                else:
                    self._bindings.pop(message_type, None)
            for widget in compact_widgets:
                if widget in self._compact_widgets:
                    self._compact_widgets.remove(widget)
            for widget in widgets.values():
                if widget in self._autofocus_widgets:
                    self._autofocus_widgets.remove(widget)

        def finalize_dismissal(value: object | None) -> None:
            remove_registrations()
            self._active_modal_ids.discard(modal_id)
            if not future.done():
                future.set_result(value)

        def dismissed(value: object | None) -> None:
            modal.set_dismissal_value(value)

        modal.set_unmount_callback(finalize_dismissal)
        modal.set_mount_callback(lambda: self._focus_widgets(
            widget for widget in widgets.values() if getattr(widget, '_textui_autofocus', False)
        ))

        self._widgets.update(widgets)
        for message_type, entries in bindings.items():
            self._bindings.setdefault(message_type, []).extend(entries)
        self._active_modal_ids.add(modal_id)
        try:
            future.mounted = self.app.push_screen(modal, callback=dismissed)
        except BaseException:
            remove_registrations()
            self._active_modal_ids.discard(modal_id)
            future.cancel()
            raise
        return future

    def dismiss_modal(self, value: object | None = None) -> None:
        screen = self.app.screen
        if not isinstance(screen, MarkupModal):
            raise DocumentStateError('No TextUI modal is active')
        screen.dismiss(value)

    def close(self) -> None:
        """Cancel lifecycle work and clear loading state during application shutdown."""
        for (_name, target_id), tasks in tuple(self._lifecycle_tasks.items()):
            for task in tasks:
                if not task.done():
                    task.cancel()
                invocation = self._lifecycle_invocations.pop(task, None)
                if invocation is not None:
                    invocation.cancelled = True
            target = self._widgets.get(target_id)
            if target is not None:
                target.remove_class("-loading")
        self._lifecycle_tasks.clear()

    def get_by_id(self, element_id: str) -> Widget:
        """Look up declared IDs only, and only while the widget is mounted."""
        if element_id not in self._declared_ids:
            raise ElementNotFoundError(f'No document element has ID {element_id!r}')
        widget = self._widgets.get(element_id)
        if widget is None or not widget.is_mounted or not self.app.is_mounted(widget):
            raise DocumentStateError(f'Element {element_id!r} is not mounted', location=self._declared_ids[element_id])
        return widget

    async def invoke_command(self, name: str) -> bool:
        """Run an enabled declared command, returning whether it ran."""
        command = self.commands.get(name)
        if command is None:
            raise DocumentStateError(f"No declared command {name!r}")
        if not command.enabled:
            return False
        try:
            result = self._command_callbacks[name]()
            if isawaitable(result):
                options = self.action_metadata.get(name)
                target_id = getattr(options, "target", None)
                target = self.get_by_id(target_id) if target_id is not None else None
                key = (name, target_id) if target_id is not None else None
                if target is not None:
                    target.add_class("-loading")
                    target.remove_class("-error")
                    target.textui_error = None

                if key is not None and getattr(options, "supersede", False):
                    for previous in tuple(self._lifecycle_tasks.get(key, ())):
                        if previous.done():
                            continue
                        previous_invocation = self._lifecycle_invocations.get(previous)
                        if previous_invocation is not None:
                            previous_invocation.cancelled = True
                        previous.cancel()

                task = asyncio.ensure_future(result)
                if key is not None:
                    self._lifecycle_tasks.setdefault(key, set()).add(task)
                    self._lifecycle_invocations[task] = ActionInvocation(target)

                def finish_lifecycle(error: Exception | None = None) -> None:
                    if key is None:
                        return
                    tasks = self._lifecycle_tasks.get(key)
                    if tasks is None:
                        return
                    tasks.discard(task)
                    self._lifecycle_invocations.pop(task, None)
                    if target is not None:
                        if error is not None:
                            target.textui_error = str(error)
                            target.add_class("-error")
                        if not tasks:
                            target.remove_class("-loading")
                    if not tasks:
                        self._lifecycle_tasks.pop(key, None)

                try:
                    await task
                except asyncio.CancelledError:
                    finish_lifecycle()
                    raise
                except Exception as error:
                    finish_lifecycle(error)
                    raise ActionExecutionError(
                        f"Command {name!r} failed: {error}",
                        location=self._command_locations.get(name),
                        value=name,
                    ) from error
                finish_lifecycle()
        except Exception as error:
            if isinstance(error, ActionExecutionError):
                raise
            raise ActionExecutionError(
                f"Command {name!r} failed: {error}",
                location=self._command_locations.get(name),
                value=name,
            ) from error
        return True

    def start_command(self, name: str) -> None:
        """Schedule a command without holding up Textual's input dispatcher."""
        task = asyncio.ensure_future(self.invoke_command(name))
        self._action_tasks.add(task)

        def report_command_result(completed: asyncio.Future[object]) -> None:
            self._action_tasks.discard(completed)
            if completed.cancelled():
                return
            try:
                completed.result()
            except Exception as error:
                self.app._handle_exception(error)

        task.add_done_callback(report_command_result)

    async def dispatch(self, message: Message) -> bool:
        """Await one exact-type/identity action without altering native bubbling."""
        for widget, event, name, node in self._bindings.get(type(message), ()):
            if event.source_widget(message) is not widget:
                continue
            if name in self.commands and not self.commands[name].enabled:
                return True
            try:
                options = self.action_metadata.get(name)
                target_id = getattr(options, "target", None)
                target = self.get_by_id(target_id) if target_id is not None else None
                key = (name, target_id) if target_id is not None else None
                if target is not None:
                    target.add_class("-loading")
                    target.remove_class("-error")
                    target.textui_error = None
                invocation = ActionInvocation(target) if target is not None else None
                result = self.actions[name](ActionContext(message, widget, self.app, self, invocation))
                if isawaitable(result):
                    if key is not None and getattr(options, "supersede", False):
                        for previous in tuple(self._lifecycle_tasks.get(key, ())):
                            if previous.done():
                                continue
                            previous_invocation = self._lifecycle_invocations.get(previous)
                            if previous_invocation is not None:
                                previous_invocation.cancelled = True
                            previous.cancel()
                    task = asyncio.ensure_future(result)
                    if key is not None:
                        self._lifecycle_tasks.setdefault(key, set()).add(task)
                        if invocation is not None:
                            self._lifecycle_invocations[task] = invocation

                    def finish_lifecycle(completed: asyncio.Future[object], error: Exception | None = None) -> None:
                        if key is None:
                            return
                        tasks = self._lifecycle_tasks.get(key)
                        if tasks is None:
                            return
                        tasks.discard(completed)
                        self._lifecycle_invocations.pop(completed, None)
                        if target is not None:
                            if error is not None:
                                target.textui_error = str(error)
                                target.add_class("-error")
                            if not tasks:
                                target.remove_class("-loading")
                        if not tasks:
                            self._lifecycle_tasks.pop(key, None)

                    await asyncio.sleep(0)
                    if task.done():
                        try:
                            await task
                        except asyncio.CancelledError:
                            finish_lifecycle(task)
                            raise
                        except Exception as error:
                            finish_lifecycle(task, error)
                            raise
                        finish_lifecycle(task)
                        return True
                    self._action_tasks.add(task)

                    def report_action_result(completed: asyncio.Future[object]) -> None:
                        self._action_tasks.discard(completed)
                        if completed.cancelled():
                            finish_lifecycle(completed)
                            return
                        try:
                            completed.result()
                        except Exception as error:
                            finish_lifecycle(completed, error)
                            action_error = ActionExecutionError(
                                f'Action {name!r} failed: {error}',
                                location=node.location,
                                value=name,
                            )
                            action_error.__cause__ = error
                            self.app._handle_exception(action_error)
                        else:
                            finish_lifecycle(completed)

                    task.add_done_callback(report_action_result)
            except Exception as error:
                raise ActionExecutionError(f'Action {name!r} failed: {error}', location=node.location, value=name) from error
            return True
        return False
