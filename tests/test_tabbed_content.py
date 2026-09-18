import pytest
from textual.widgets import TabbedContent, TabPane

from textui import DocumentLoader, DocumentValidationError, TextUI


MARKUP = '''<ui><tabbed-content id="tabs" initial="home" on-tab-activated="selected">
  <tab-pane id="home" title="Home"><label id="home-label">Welcome</label></tab-pane>
  <tab-pane id="settings" title="Settings"><label id="settings-label">Preferences</label></tab-pane>
</tabbed-content></ui>'''


@pytest.mark.asyncio
async def test_tabbed_content_uses_native_panes_and_emits_selected_event():
    selected = []
    app = TextUI(DocumentLoader().from_string(MARKUP), actions={"selected": lambda context: selected.append(context.event.pane.id)})
    async with app.run_test() as pilot:
        tabs = app.document.get_by_id("tabs")
        assert isinstance(tabs, TabbedContent)
        assert isinstance(app.document.get_by_id("home"), TabPane)
        assert tabs.active == "home"
        selected.clear()
        tabs.active = "settings"
        await pilot.pause()
        assert tabs.active == "settings"
        assert selected == ["settings"]


@pytest.mark.parametrize("markup", [
    '<ui><tab-pane id="x" title="X"/></ui>',
    '<ui><tabbed-content><label>Wrong</label></tabbed-content></ui>',
    '<ui><tabbed-content initial="missing"><tab-pane id="x" title="X"/></tabbed-content></ui>',
    '<ui><tabbed-content><tab-pane title="No id"/></tabbed-content></ui>',
])
def test_tabbed_content_rejects_invalid_structure(markup: str):
    with pytest.raises(DocumentValidationError):
        DocumentLoader().from_string(markup)
