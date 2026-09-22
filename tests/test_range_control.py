import pytest

from textui import DocumentLoader, DocumentValidationError, TextUI
from textui.widgets.range_control import RangeControl


MARKUP = '''<ui>
  <range id="volume" min="10" max="20" step="2" value="14" show-value="true" on-changed="record" />
</ui>'''


def test_range_lowers_integer_attributes_and_defaults():
    document = DocumentLoader().from_string(MARKUP)
    node = document.nodes[0]
    assert node.attributes == {
        "min": 10,
        "max": 20,
        "step": 2,
        "value": 14,
        "show-value": True,
    }

    default = DocumentLoader().from_string('<ui><range id="default" /></ui>').nodes[0]
    assert default.attributes == {
        "min": 0,
        "max": 100,
        "step": 1,
        "value": 0,
        "show-value": False,
    }

    custom_minimum = DocumentLoader().from_string('<ui><range min="25" max="50" /></ui>').nodes[0]
    assert custom_minimum.attributes["value"] == 25


@pytest.mark.parametrize("markup", [
    '<ui><range min="10" max="10" /></ui>',
    '<ui><range min="0" max="10" step="0" /></ui>',
    '<ui><range min="0" max="10" step="3" /></ui>',
    '<ui><range min="0" max="10" value="11" /></ui>',
    '<ui><range min="0" max="10" step="2" value="3" /></ui>',
])
def test_range_rejects_invalid_bounds_step_and_value(markup: str):
    with pytest.raises(DocumentValidationError):
        DocumentLoader().from_string(markup)


@pytest.mark.asyncio
async def test_range_dispatches_changed_values_for_keyboard_and_controller_updates():
    seen = []
    app = TextUI(
        DocumentLoader().from_string(MARKUP),
        actions={"record": lambda context: seen.append(context.event.value)},
    )
    async with app.run_test(size=(40, 8)) as pilot:
        await pilot.pause()
        volume = app.document.get_by_id("volume")
        assert isinstance(volume, RangeControl)
        assert volume.value == 14

        volume.focus()
        await pilot.press("right", "end", "home")
        await pilot.pause()
        assert volume.value == 10
        assert seen == [16, 20, 10]

        volume.value = 18
        await pilot.pause()
        assert seen == [16, 20, 10, 18]


@pytest.mark.asyncio
async def test_range_pointer_and_disabled_state_control_value_changes():
    app = TextUI(DocumentLoader().from_string(
        '<ui><range id="range" min="0" max="10" step="1" value="0" /><range id="locked" value="5" disabled="true" /></ui>'
    ))
    async with app.run_test(size=(30, 8)) as pilot:
        await pilot.pause()
        control = app.document.get_by_id("range")
        locked = app.document.get_by_id("locked")
        await pilot.click(control, offset=(control.region.width - 1, 0))
        await pilot.pause()
        assert control.value == 10

        control.value = 0
        await pilot.mouse_down(control, offset=(0, 0))
        end = (control.region.x + control.region.width - 1, control.region.y)
        await pilot.hover(offset=end)
        await pilot.mouse_up(offset=end)
        await pilot.pause()
        assert control.value == 10

        locked.focus()
        await pilot.press("right")
        await pilot.click(locked, offset=(locked.region.width - 1, 0))
        await pilot.pause()
        assert locked.value == 5


@pytest.mark.asyncio
async def test_range_renders_a_thumb_track_and_optional_value():
    app = TextUI(DocumentLoader().from_string(
        '<ui><range id="range" min="0" max="20" step="5" value="10" show-value="true" /></ui>'
    ))
    async with app.run_test(size=(30, 4)) as pilot:
        await pilot.pause()
        control = app.document.get_by_id("range")
        rendered = control.render()
        assert rendered.plain.count("●") == 1
        assert rendered.plain.endswith(" 10")
        assert len(rendered.plain) == control.content_size.width


@pytest.mark.asyncio
async def test_range_reserves_value_space_for_a_negative_minimum():
    app = TextUI(DocumentLoader().from_string(
        '<ui><range id="range" min="-100" max="0" value="-100" show-value="true" /></ui>'
    ))
    async with app.run_test(size=(10, 4)) as pilot:
        await pilot.pause()
        control = app.document.get_by_id("range")
        assert len(control.render().plain) == control.content_size.width
