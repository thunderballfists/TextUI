import pytest

from textui import ComponentBuildError, DocumentLoader, TextUI
from textui.widgets.split import Pane, Split


def split_app(markup: str = '<ui><split id="split" direction="horizontal"><pane id="side" min-size="10" size="20"><label>Side</label></pane><pane id="main" min-size="20"><label>Main</label></pane></split></ui>'):
    return TextUI(DocumentLoader().from_string(markup))


@pytest.mark.asyncio
async def test_split_mounts_two_panes_with_internal_divider_and_keyboard_resize():
    app = split_app()
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        split = app.document.get_by_id("split")
        side = app.document.get_by_id("side")
        assert isinstance(split, Split)
        assert isinstance(side, Pane)
        assert split.divider.id is None
        assert side.region.width == 20
        split.divider.focus()
        await pilot.press("right")
        await pilot.pause()
        assert side.region.width == 21


@pytest.mark.asyncio
async def test_split_drag_clamps_and_hide_show_restores_size():
    app = split_app()
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        split = app.document.get_by_id("split")
        side = app.document.get_by_id("side")
        await pilot.mouse_down(split.divider)
        await pilot.hover(offset=(35, 2))
        await pilot.mouse_up(offset=(35, 2))
        await pilot.pause()
        assert side.region.width == 35
        side.display = False
        await pilot.pause()
        assert split.divider.display is False
        side.display = True
        await pilot.pause()
        assert side.region.width == 35
        await pilot.resize_terminal(25, 24)
        await pilot.pause()
        assert side.region.width <= 10


@pytest.mark.asyncio
async def test_split_rejects_other_child_types_before_mount():
    app = split_app('<ui><split><label>Wrong</label><pane /></split></ui>')
    with pytest.raises(ComponentBuildError, match="pane"):
        async with app.run_test():
            pass


@pytest.mark.asyncio
async def test_split_resized_event_dispatches_declared_action():
    seen = []
    markup = '<ui><split id="split" on-resized="record"><pane size="20"/><pane/></split></ui>'
    app = TextUI(DocumentLoader().from_string(markup), actions={"record": lambda context: seen.append(context.event.size)})
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        app.document.get_by_id("split").resize_first(30)
        await pilot.pause()
    assert seen == [30]
