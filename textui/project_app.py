"""Native Textual App host for a discovered TextUI project."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Button, Checkbox, Collapsible, DataTable, Input, RadioButton, RadioSet, Select, Switch, TabbedContent, TextArea, Tree
from .widgets.split import Split
from .widgets.navigation import Nav
from .widgets.runtime_list import RuntimeList
from .accelerators import activate_tab, install_tab_accelerators, tab_accelerators

from .actions import ActionCallback
from .controllers import ControllerSet, ProjectWindow
from .document import BoundDocument
from .errors import DocumentValidationError
from .project import ProjectSource
from .widgets.builtin_widgets import default_component_registry


class ProjectApp(App):
    def __init__(self, source: ProjectSource, *, actions: Mapping[str, ActionCallback] | None = None, **app_options: Any) -> None:
        super().__init__(**app_options)
        self.source = source
        self.window = ProjectWindow(self, default_component_registry())
        self.controllers = ControllerSet(self.window)
        self._host_actions = dict(actions or {})
        self.document: BoundDocument | None = None
        self._setup_completed = False
        self._closed = False

    async def on_load(self) -> None:
        try:
            for path in self.source.scripts:
                self.controllers.load(path)
            duplicates = set(self.controllers.actions) & set(self._host_actions)
            if duplicates:
                raise DocumentValidationError(f"duplicate action {sorted(duplicates)[0]!r}")
            self.window.phase = "setup"
            self._setup_completed = True
            await self.controllers.hook("on_setup")
            definition = self.source.lower(self.window.registry)
            self._textui_loading = True
            try:
                self.document = definition.bind(
                    self,
                    actions={**self._host_actions, **self.controllers.actions},
                    commands=self.controllers.commands,
                    command_callbacks=self.controllers.command_callbacks,
                    command_locations=self.controllers.command_locations,
                )
            finally:
                self._textui_loading = False
            self.window._document = self.document
            tab_keys = {key for key, _pane_id in tab_accelerators(definition.nodes)}
            for name, command in self.controllers.commands.items():
                if command.shortcut in tab_keys:
                    raise DocumentValidationError(
                        f"command shortcut {command.shortcut!r} conflicts with tab accelerator {command.shortcut!r}",
                        location=self.controllers.command_locations[name],
                    )
            install_tab_accelerators(self, definition.nodes)
            for name, command in self.controllers.commands.items():
                if command.shortcut is not None:
                    self._bindings.bind(
                        command.shortcut,
                        f"textui_invoke_command('{name}')",
                        command.description,
                        priority=True,
                    )
                    bindings = self._bindings.get_bindings_for_key(command.shortcut)
                    bindings.insert(0, bindings.pop())
            self.window.phase = "bound"
        except BaseException:
            if self._setup_completed:
                await self._close_once()
            raise

    def compose(self) -> ComposeResult:
        if self.document is None:
            raise RuntimeError("project document has not been bound")
        yield from self.document.compose()

    def action_textui_activate_tab(self, pane_id: str) -> None:
        if self.document is None:
            raise RuntimeError("project document has not been bound")
        activate_tab(self.document, pane_id)

    async def action_textui_invoke_command(self, command_name: str) -> None:
        if self.document is None:
            raise RuntimeError("project document has not been bound")
        await self.document.invoke_command(command_name)

    async def on_mount(self) -> None:
        self.window.phase = "ready"
        await self.controllers.hook("on_ready")
        if self.window.phase != "ready":
            return
        for seconds, callback, thread in self.controllers.periodic:
            self.window.every(seconds, callback, thread=thread)

    async def on_unmount(self) -> None:
        await self._close_once()

    def exit(self, result: Any = None, return_code: int = 0, message: Any = None) -> None:
        """Stop project-owned timers before Textual starts application teardown."""
        if self.window.phase == "ready":
            self.window.phase = "closing"
            self.window.timers.close()
        super().exit(result=result, return_code=return_code, message=message)

    async def _close_once(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.window.phase = "closing"
        self.window.timers.close()
        try:
            await self.controllers.hook("on_close")
        finally:
            self.window.phase = "closed"

    @on(Button.Pressed)
    @on(Input.Changed)
    @on(Input.Submitted)
    @on(Checkbox.Changed)
    @on(Split.Resized)
    @on(Split.Toggled)
    @on(Nav.Selected)
    @on(Select.Changed)
    @on(Switch.Changed)
    @on(TextArea.Changed)
    @on(TabbedContent.TabActivated)
    @on(RadioButton.Changed)
    @on(RadioSet.Changed)
    @on(Collapsible.Collapsed)
    @on(Collapsible.Expanded)
    @on(DataTable.RowSelected)
    @on(DataTable.CellSelected)
    @on(Tree.NodeSelected)
    @on(RuntimeList.ItemSelected)
    async def forward_document_message(self, event: Button.Pressed | Input.Changed | Input.Submitted | Checkbox.Changed | Split.Resized | Split.Toggled | Nav.Selected | Select.Changed | Switch.Changed | TextArea.Changed | TabbedContent.TabActivated | RadioButton.Changed | RadioSet.Changed | Collapsible.Collapsed | Collapsible.Expanded | DataTable.RowSelected | DataTable.CellSelected | Tree.NodeSelected | RuntimeList.ItemSelected) -> None:
        if self.document is not None:
            await self.document.dispatch(event)
