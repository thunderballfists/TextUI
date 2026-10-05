import pytest
from textual.screen import Screen
from textual.containers import Vertical

from textui import ComponentRegistry, ComponentSpec, DocumentLoader, DocumentValidationError, ElementNotFoundError, ProjectApp, ProjectSource, TextUI
from textui.widgets.builtin_widgets import default_component_registry
from textui.widgets.tabbed import register_tabs


MARKUP = '''<ui>
  <horizontal>
    <input id="prompt" />
    <tabbed-content id="detail" initial="dashboard">
      <tab-pane id="dashboard" title="Dashboard" accelerator="d" accelerator-scope="document"><label>Dashboard</label></tab-pane>
      <tab-pane id="usage" title="Usage" accelerator="u" accelerator-scope="document"><label>Usage</label></tab-pane>
    </tabbed-content>
  </horizontal>
</ui>'''


def test_tab_accelerators_require_unique_single_keys_and_document_scope():
    DocumentLoader().from_string(MARKUP)
    for markup in [
        MARKUP.replace('accelerator="u"', 'accelerator="d"'),
        MARKUP.replace('accelerator="u"', 'accelerator="up"'),
        MARKUP.replace('accelerator="u"', 'accelerator="?"'),
        MARKUP.replace('accelerator-scope="document"', 'accelerator-scope="pane"'),
        MARKUP.replace(' accelerator-scope="document"', ''),
        MARKUP.replace('</ui>', '''<tabbed-content><tab-pane id="other" title="Other" accelerator="u" accelerator-scope="document"/></tabbed-content></ui>'''),
    ]:
        with pytest.raises(DocumentValidationError):
            DocumentLoader().from_string(markup)


@pytest.mark.asyncio
async def test_document_accelerator_switches_tabs_when_another_pane_has_focus():
    app = TextUI(DocumentLoader().from_string(MARKUP))
    async with app.run_test() as pilot:
        prompt = app.document.get_by_id("prompt")
        tabs = app.document.get_by_id("detail")
        prompt.blur()
        await pilot.press("u")
        await pilot.pause()
        assert tabs.active == "usage"
        assert app.focused is not prompt


@pytest.mark.asyncio
async def test_printable_accelerator_is_literal_while_an_input_has_focus():
    app = TextUI(DocumentLoader().from_string(MARKUP))
    async with app.run_test() as pilot:
        prompt = app.document.get_by_id("prompt")
        tabs = app.document.get_by_id("detail")
        prompt.focus()
        await pilot.press("u")
        await pilot.pause()
        assert prompt.value == "u"
        assert tabs.active == "dashboard"


@pytest.mark.asyncio
async def test_custom_container_named_modal_keeps_main_screen_accelerators():
    registry = ComponentRegistry()
    registry.register(ComponentSpec("modal", lambda context: Vertical(*context.children), child_policy="widgets"))
    register_tabs(registry)
    definition = DocumentLoader(registry).from_string('''<ui><modal>
      <tabbed-content id="tabs" initial="home">
        <tab-pane id="home" title="Home"/>
        <tab-pane id="details" title="Details" accelerator="d" accelerator-scope="document"/>
      </tabbed-content>
    </modal></ui>''')
    app = TextUI(definition)
    async with app.run_test() as pilot:
        await pilot.press("d")
        assert app.document.get_by_id("tabs").active == "details"


@pytest.mark.asyncio
@pytest.mark.parametrize("host", ["document", "project"])
@pytest.mark.parametrize("in_modal", [False, True])
async def test_component_private_tab_accelerator_preserves_public_id_isolation(tmp_path, host, in_modal):
    (tmp_path / "tabs.ui").write_text('''<component>
      <tabbed-content initial="home">
        <tab-pane id="home" title="Home"><label>Home</label></tab-pane>
        <tab-pane id="details" title="Details" accelerator="d" accelerator-scope="document"><label>Details</label></tab-pane>
      </tabbed-content>
    </component>''', encoding="utf-8")
    content = '<app-tabs id="tabs"/>'
    if in_modal:
        content = f'<modal id="help">{content}</modal>'
    (tmp_path / "app.ui").write_text(f'<ui><component src="tabs.ui" as="app-tabs"/>{content}</ui>', encoding="utf-8")
    source = ProjectSource.discover(tmp_path / "app.ui")
    app = ProjectApp(source) if host == "project" else TextUI(source.lower(default_component_registry()))
    async with app.run_test() as pilot:
        if in_modal:
            result = app.document.push_modal("help")
            await result.mounted
            await pilot.pause()
        tabs = app.document.get_by_id("tabs")
        private_id = tabs.active.replace("home", "details")
        with pytest.raises(ElementNotFoundError):
            app.document.get_by_id(private_id)
        await pilot.press("d")
        assert tabs.active == private_id
        with pytest.raises(ElementNotFoundError):
            app.document.get_by_id(private_id)
        if in_modal:
            await pilot.press("escape")
            await result
            assert await app.run_action(f"textui_activate_tab('{private_id}')") is False


@pytest.mark.asyncio
@pytest.mark.parametrize("host", ["document", "project"])
async def test_modal_accelerators_follow_active_screen_and_reopening(tmp_path, host):
    markup = '''<ui>
      <tabbed-content id="main-tabs" initial="main-home">
        <tab-pane id="main-home" title="Home"/>
        <tab-pane id="main-details" title="Details" accelerator="d" accelerator-scope="document"/>
      </tabbed-content>
      <modal id="help">
        <tabbed-content id="modal-tabs" initial="modal-home" style="height: 5; width: 40;">
          <tab-pane id="modal-home" title="Home"/>
          <tab-pane id="modal-details" title="Details" accelerator="m" accelerator-scope="document"/>
        </tabbed-content>
      </modal>
    </ui>'''
    (tmp_path / "app.ui").write_text(markup, encoding="utf-8")
    app = ProjectApp(ProjectSource.discover(tmp_path / "app.ui")) if host == "project" else TextUI(DocumentLoader().from_string(markup))
    async with app.run_test() as pilot:
        main = app.document.get_by_id("main-tabs")
        assert await app.run_action("textui_activate_tab('modal-details')") is False
        await pilot.press("m")
        assert main.active == "main-home"
        for _ in range(2):
            result = app.document.push_modal("help")
            await result.mounted
            await pilot.pause()
            modal = app.document.get_by_id("modal-tabs")
            assert modal.active == "modal-home"
            assert await app.run_action("textui_activate_tab('main-details')") is False
            await pilot.press("d", "m")
            assert main.active == "main-home"
            assert modal.active == "modal-details"
            await pilot.press("escape")
            await result
            assert await app.run_action("textui_activate_tab('modal-details')") is False
            await pilot.press("m")
        await app.push_screen(Screen())
        assert await app.run_action("textui_activate_tab('main-details')") is False
        await pilot.press("d")
        assert main.active == "main-home"
        await app.pop_screen()
        await pilot.press("d")
        assert main.active == "main-details"
