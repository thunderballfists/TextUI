import pytest

from textui import ComponentBuildError, DocumentLoader, DocumentValidationError, TextUI
from textui.widgets.navigation import Nav, NavItem


MARKUP = '''<ui>
<horizontal>
  <nav id="menu" on-selected="show">
    <nav-item target="home">Home</nav-item>
    <nav-item target="settings">Settings</nav-item>
  </nav>
  <content-switcher id="content" initial="home">
    <vertical id="home"><label>Home page</label></vertical>
    <vertical id="settings"><label>Settings page</label></vertical>
  </content-switcher>
</horizontal>
</ui>'''


@pytest.mark.asyncio
async def test_nav_mouse_and_keyboard_selection_switches_native_content():
    seen = []

    def show(context):
        seen.append(context.event.target)
        context.document.get_by_id("content").current = context.event.target

    app = TextUI(DocumentLoader().from_string(MARKUP), actions={"show": show})
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        nav = app.document.get_by_id("menu")
        assert isinstance(nav, Nav)
        assert isinstance(nav.items[1], NavItem)
        assert await pilot.click(nav.items[1])
        await pilot.pause()
        assert seen == ["settings"]
        assert app.document.get_by_id("content").current == "settings"
        nav.items[0].focus()
        await pilot.press("enter")
        await pilot.pause()
        assert seen == ["settings", "home"]


def test_nav_rejects_missing_target_before_mount():
    invalid = MARKUP.replace('target="settings"', 'target="absent"')
    with pytest.raises(DocumentValidationError, match="target"):
        DocumentLoader().from_string(invalid)


@pytest.mark.asyncio
async def test_nav_rejects_non_item_children():
    app = TextUI(DocumentLoader().from_string('<ui><nav><label>Wrong</label></nav></ui>'))
    with pytest.raises(ComponentBuildError, match="nav-item"):
        async with app.run_test():
            pass
