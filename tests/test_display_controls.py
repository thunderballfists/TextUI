import pytest
from textual.widgets import Collapsible, ProgressBar, RadioButton, RadioSet, Rule

from textui import DocumentLoader, DocumentValidationError, TextUI


@pytest.mark.asyncio
async def test_autofocus_moves_keyboard_focus_to_a_declared_control_after_mount():
    app = TextUI(DocumentLoader().from_string('''<ui>
      <input id="prompt" autofocus="true" />
      <button id="send">Send</button>
    </ui>'''))
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.focused is app.document.get_by_id("prompt")


@pytest.mark.asyncio
async def test_modal_autofocus_moves_focus_when_the_modal_is_revealed():
    app = TextUI(DocumentLoader().from_string('''<ui>
      <button id="open" on-pressed="open_modal">Open</button>
      <modal id="dialog"><input id="prompt" autofocus="true" /></modal>
    </ui>'''), actions={"open_modal": lambda context: context.push_modal("dialog")})
    async with app.run_test() as pilot:
        assert await pilot.click("#open")
        await pilot.pause()
        assert app.focused is app.document.get_by_id("prompt")


MARKUP = '''<ui>
  <radio-set id="choice" on-changed="choose">
    <radio-button id="alpha">Alpha</radio-button>
    <radio-button id="beta" value="true">Beta</radio-button>
  </radio-set>
  <collapsible id="details" title="Details" collapsed="false" on-collapsed="collapse" on-expanded="expand">
    <label id="detail-label">More information</label>
  </collapsible>
  <progress-bar id="work" total="10" progress="2.5" show-eta="false" />
  <rule id="divider" orientation="horizontal" line-style="heavy" />
</ui>'''


def test_display_controls_lower_typed_attributes():
    document = DocumentLoader().from_string(MARKUP)
    radio, collapsible, progress, rule = document.nodes
    assert radio.children[1].attributes["value"] is True
    assert collapsible.attributes["collapsed"] is False
    assert progress.attributes["total"] == 10.0
    assert progress.attributes["progress"] == 2.5
    assert rule.attributes["line-style"] == "heavy"


def test_radio_button_in_a_set_rejects_unreachable_changed_action():
    with pytest.raises(DocumentValidationError, match="radio-set"):
        DocumentLoader().from_string('''<ui>
          <radio-set><radio-button on-changed="choose">Choice</radio-button></radio-set>
        </ui>''')


@pytest.mark.parametrize("markup", [
    '<ui><radio-set><label>Wrong</label></radio-set></ui>',
    '<ui><radio-set><radio-button value="true">A</radio-button><radio-button value="true">B</radio-button></radio-set></ui>',
    '<ui><progress-bar total="0"/></ui>',
    '<ui><progress-bar progress="nan"/></ui>',
    '<ui><progress-bar total="2" progress="3"/></ui>',
    '<ui><rule line-style="wavy"/></ui>',
])
def test_display_controls_reject_invalid_structure_and_values(markup):
    with pytest.raises(DocumentValidationError):
        DocumentLoader().from_string(markup)


@pytest.mark.asyncio
async def test_native_display_controls_and_events():
    events = []
    actions = {
        "choose": lambda context: events.append(("radio", context.event.pressed.id)),
        "collapse": lambda context: events.append(("collapsed", context.widget.id)),
        "expand": lambda context: events.append(("expanded", context.widget.id)),
    }
    app = TextUI(DocumentLoader().from_string(MARKUP), actions=actions)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        radio = app.document.get_by_id("choice")
        details = app.document.get_by_id("details")
        progress = app.document.get_by_id("work")
        divider = app.document.get_by_id("divider")
        assert isinstance(radio, RadioSet)
        assert isinstance(app.document.get_by_id("beta"), RadioButton)
        assert radio.pressed_button.id == "beta"
        assert isinstance(details, Collapsible) and details.collapsed is False
        assert isinstance(progress, ProgressBar) and progress.progress == 2.5
        assert isinstance(divider, Rule) and divider.line_style == "heavy"
        events.clear()
        await pilot.click("#alpha")
        await pilot.pause()
        assert ("radio", "alpha") in events
        details.collapsed = True
        await pilot.pause()
        assert ("collapsed", "details") in events
        details.collapsed = False
        await pilot.pause()
        assert ("expanded", "details") in events
        progress.update(advance=2.5)
        assert progress.progress == 5.0
