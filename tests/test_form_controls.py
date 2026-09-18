import pytest
from textual.widgets import Select, Switch, TextArea

from textui import DocumentLoader, DocumentValidationError, TextUI


def load(markup: str):
    return DocumentLoader().from_string(markup, source_name="controls.ui")


def test_select_options_switch_and_verbatim_text_area_lower_as_markup():
    document = load('''<ui>
      <select id="state" value="open" allow-blank="false" prompt="State">
        <option value="open">Open</option><option value="closed">Closed</option>
      </select>
      <switch id="enabled" value="true" />
      <text-area id="notes" soft-wrap="false">first\n  second</text-area>
    </ui>''')

    select, switch, area = document.nodes
    assert select.children[0].attributes["value"] == "open"
    assert select.children[1].text == "Closed"
    assert switch.attributes["value"] is True
    assert area.text == "first\n  second"


@pytest.mark.parametrize("markup", [
    '<ui><option value="x">X</option></ui>',
    '<ui><select><label>Wrong</label></select></ui>',
    '<ui><select><option value="x">X</option><option value="x">Again</option></select></ui>',
    '<ui><select value="missing"><option value="x">X</option></select></ui>',
    '<ui><text-area><label>Nested</label></text-area></ui>',
])
def test_form_controls_reject_invalid_structure_and_values(markup: str):
    with pytest.raises(DocumentValidationError):
        load(markup)


@pytest.mark.asyncio
async def test_form_control_events_dispatch_with_native_widgets():
    seen = []
    document = load('''<ui>
      <select id="state" on-changed="changed" value="open" allow-blank="false">
        <option value="open">Open</option><option value="closed">Closed</option>
      </select>
      <switch id="enabled" on-changed="changed" />
      <text-area id="notes" on-changed="changed">Before</text-area>
    </ui>''')
    app = TextUI(document, actions={"changed": lambda context: seen.append(context.widget.id)})
    async with app.run_test() as pilot:
        state = app.document.get_by_id("state")
        enabled = app.document.get_by_id("enabled")
        notes = app.document.get_by_id("notes")
        assert isinstance(state, Select) and state.value == "open"
        assert isinstance(enabled, Switch) and enabled.value is False
        assert isinstance(notes, TextArea) and notes.text == "Before"
        seen.clear()
        state.value = "closed"
        enabled.value = True
        notes.text = "After"
        await pilot.pause()
        assert {"state", "enabled", "notes"}.issubset(seen)
