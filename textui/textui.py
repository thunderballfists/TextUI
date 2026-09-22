"""Thin native Textual App convenience for a validated Document."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Button, Checkbox, Collapsible, DataTable, Input, RadioButton, RadioSet, Select, Switch, TabbedContent, TextArea, Tree
from .widgets.split import Split
from .widgets.navigation import Nav
from .widgets.runtime_list import RuntimeList
from .widgets.range_control import RangeControl
from .accelerators import activate_tab, install_tab_accelerators

from .actions import ActionCallback
from .document import Document


class TextUI(App):
    def __init__(self, document: Document, *, actions: Mapping[str, ActionCallback] | None = None, **app_options: Any) -> None:
        super().__init__(**app_options)
        self.document = document.bind(self, actions={} if actions is None else actions)
        install_tab_accelerators(self, document.nodes)

    def compose(self) -> ComposeResult:
        yield from self.document.compose()

    def action_textui_activate_tab(self, pane_id: str) -> None:
        activate_tab(self.document, pane_id)

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
    @on(RangeControl.Changed)
    async def forward_document_message(self, event: Button.Pressed | Input.Changed | Input.Submitted | Checkbox.Changed | Split.Resized | Split.Toggled | Nav.Selected | Select.Changed | Switch.Changed | TextArea.Changed | TabbedContent.TabActivated | RadioButton.Changed | RadioSet.Changed | Collapsible.Collapsed | Collapsible.Expanded | DataTable.RowSelected | DataTable.CellSelected | Tree.NodeSelected | RuntimeList.ItemSelected | RangeControl.Changed) -> None:
        await self.document.dispatch(event)
