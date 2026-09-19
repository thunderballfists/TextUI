"""Immutable document definitions and single-use native runtime bindings."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from inspect import isawaitable
from types import MappingProxyType
from weakref import WeakSet

from textual.app import App
from textual.message import Message
from textual.widget import Widget

from .actions import ActionCallback, ActionContext
from .errors import (
    ActionExecutionError, ComponentBuildError, DocumentStateError,
    DocumentValidationError, ElementNotFoundError,
)
from .nodes import ElementNode, StyleBlock
from .registry import BuildContext, EventSpec
from .widgets.modal import MarkupModal
from .styling import apply_inline, commit_styles, prepare_styles

# A factory may not recycle an instance across bindings, even before mounting.
_built_widgets: WeakSet[Widget] = WeakSet()


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

    def bind(self, app: App, *, actions: Mapping[str, ActionCallback]) -> BoundDocument:
        """Validate callbacks and reserve one binding on an initialized App."""
        if not isinstance(app, App) or not hasattr(app, 'stylesheet'):
            raise DocumentStateError('Bind to an initialized Textual App')
        if app.is_running and not getattr(app, "_textui_loading", False):
            raise DocumentStateError('Bind the document before running the App')
        if hasattr(app, '_textui_document_binding'):
            raise DocumentStateError('An App may have only one document binding')
        callbacks = dict(actions)
        for node in _walk(self.nodes):
            for event_name, name in node.events.items():
                if name not in callbacks or not callable(callbacks[name]):
                    raise DocumentValidationError(f'Action {name!r} must be exposed as a callable', location=node.location, attribute=f'on-{event_name}', value=name)
        for name, callback in callbacks.items():
            if not isinstance(name, str) or not name.isidentifier() or not callable(callback):
                raise DocumentValidationError(f'Action {name!r} must have an identifier name and a callable value')
        bound = BoundDocument(self, app, callbacks)
        app._textui_document_binding = bound
        return bound


class BoundDocument:
    """One App's callbacks, constructed tree, and native message bindings."""

    def __init__(self, definition: Document, app: App, actions: Mapping[str, ActionCallback]) -> None:
        self.definition = definition
        self.app = app
        self.actions = MappingProxyType(dict(actions))
        self._state = 'bound'
        self._declared_ids = {node.common['id']: node.location for node in _walk(definition.nodes) if node.common['id'] is not None and not node.private_id}
        self._widgets: dict[str, Widget] = {}
        self._bindings: dict[type, list[tuple[Widget, EventSpec, str, ElementNode]]] = {}
        self._modal_nodes = {
            node.common["id"]: node
            for node in definition.nodes
            if node.spec.tag == "modal" and node.common["id"] is not None
        }

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
        except Exception as error:
            raise ComponentBuildError(str(error), location=node.location) from error
        if node.common['style'] is not None:
            apply_inline(widget, node.common['style'], node.location)
        if node.common['id'] is not None and not node.private_id:
            widgets[node.common['id']] = widget
        for event_name, action in node.events.items():
            event = node.spec.events[event_name]
            bindings.setdefault(event.message_type, []).append((widget, event, action, node))
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
            roots = tuple(self._build_node(node, widgets, bindings) for node in self.definition.nodes if node.spec.tag != "modal")
            commit_styles(self.app, staged)
        except BaseException:
            self._state = 'failed'
            raise
        self._widgets, self._bindings = widgets, bindings
        self._state = 'prepared'
        return iter(roots)

    def push_modal(self, modal_id: str):
        """Push a declared modal and return a future resolved by dismissal."""
        import asyncio

        node = self._modal_nodes.get(modal_id)
        if node is None:
            raise ElementNotFoundError(f'No declared modal has ID {modal_id!r}')
        widgets: dict[str, Widget] = {}
        bindings: dict[type, list[tuple[Widget, EventSpec, str, ElementNode]]] = {}
        modal = self._build_node(node, widgets, bindings)
        if not isinstance(modal, MarkupModal):
            raise DocumentStateError(f'Element {modal_id!r} is not a modal')
        self._widgets.update(widgets)
        for message_type, entries in bindings.items():
            self._bindings.setdefault(message_type, []).extend(entries)
        future: asyncio.Future[object | None] = asyncio.get_running_loop().create_future()
        modal_widgets = set(widgets.values())

        def dismissed(value: object | None) -> None:
            for element_id, widget in widgets.items():
                if self._widgets.get(element_id) is widget:
                    self._widgets.pop(element_id)
            for message_type, entries in bindings.items():
                self._bindings[message_type] = [entry for entry in self._bindings[message_type] if entry[0] not in modal_widgets]
            future.set_result(value)

        self.app.push_screen(modal, callback=dismissed)
        return future

    def dismiss_modal(self, value: object | None = None) -> None:
        screen = self.app.screen
        if not isinstance(screen, MarkupModal):
            raise DocumentStateError('No TextUI modal is active')
        screen.dismiss(value)

    def get_by_id(self, element_id: str) -> Widget:
        """Look up declared IDs only, and only while the widget is mounted."""
        if element_id not in self._declared_ids:
            raise ElementNotFoundError(f'No document element has ID {element_id!r}')
        widget = self._widgets.get(element_id)
        if widget is None or not widget.is_mounted or not self.app.is_mounted(widget):
            raise DocumentStateError(f'Element {element_id!r} is not mounted', location=self._declared_ids[element_id])
        return widget

    async def dispatch(self, message: Message) -> bool:
        """Await one exact-type/identity action without altering native bubbling."""
        for widget, event, name, node in self._bindings.get(type(message), ()):
            if event.source_widget(message) is not widget:
                continue
            try:
                result = self.actions[name](ActionContext(message, widget, self.app, self))
                if isawaitable(result):
                    import asyncio

                    task = asyncio.create_task(result)
                    await asyncio.sleep(0)
                    if task.done():
                        await task
            except Exception as error:
                raise ActionExecutionError(f'Action {name!r} failed: {error}', location=node.location, value=name) from error
            return True
        return False
