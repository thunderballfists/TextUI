import pytest

from textui import DocumentLoader, DocumentValidationError, TextUI


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
