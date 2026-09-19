"""Exercise visible showcase controls through real pointer geometry."""

from pathlib import Path

import pytest
from textual.widgets import Button

from textui import DocumentLoader, TextUI
from textui.widgets.bars import SlotBar


ENTRY = Path(__file__).parents[1] / "examples" / "showcase" / "app.ui"


def showcase_app():
    from textui import ProjectApp, ProjectSource

    return ProjectApp(ProjectSource.discover(ENTRY))


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [(120, 50), (80, 24), (60, 20)])
async def test_showcase_shell_controls_remain_visible_and_toggle_sidebar(size):
    """A clipped shell would hide feedback or make the sidebar toggle unreachable."""
    app = showcase_app()
    async with app.run_test(size=size) as pilot:
        await pilot.pause(0.25)
        bars = list(app.screen.query(SlotBar))
        feedback = app.document.get_by_id("feedback")
        toggle = app.document.get_by_id("toggle-sidebar")
        assert len(bars) == 2
        assert all(bar.region.height > 0 and app.screen.region.contains_region(bar.region) for bar in bars)
        assert feedback.region.height > 0
        assert app.screen.region.contains_region(feedback.region)
        assert toggle.region.width > 0 and toggle.region.height > 0
        assert app.screen.region.contains_region(toggle.region)
        assert await pilot.click(toggle, offset=(toggle.region.width // 2, toggle.region.height // 2))
        await pilot.pause(0.25)
        assert app.document.get_by_id("sidebar").display is False
        x = toggle.region.x + toggle.region.width // 2
        y = toggle.region.y + toggle.region.height // 2
        assert app.get_widget_at(x, y)[0] is toggle
        assert await pilot.click(toggle, offset=(toggle.region.width // 2, toggle.region.height // 2))
        await pilot.pause(0.25)
        assert app.document.get_by_id("sidebar").display is True


@pytest.mark.asyncio
async def test_showcase_data_and_activity_controls_are_pointer_reachable():
    """Navigation must lead to data and modal controls that a mouse can activate."""
    app = showcase_app()
    async with app.run_test(size=(80, 24)) as pilot:
        navigation = app.document.get_by_id("navigation")
        assert await pilot.click(navigation.items[2])
        await pilot.pause(0.25)
        add_data = app.document.get_by_id("add-data")
        add_data.scroll_visible(animate=False)
        await pilot.pause()
        assert await pilot.click(add_data)
        await pilot.pause()
        assert app.document.get_by_id("jobs").get_cell("deploy", "state") == "Queued"
        assert await pilot.click(navigation.items[3])
        await pilot.pause()
        open_modal = app.document.get_by_id("open-modal")
        open_modal.scroll_visible(animate=False)
        await pilot.pause()
        assert await pilot.click(open_modal)
        await pilot.pause()
        close_modal = app.document.get_by_id("close-modal")
        x = close_modal.region.x + close_modal.region.width // 2
        y = close_modal.region.y + close_modal.region.height // 2
        assert app.get_widget_at(x, y)[0] is close_modal
        assert await pilot.click(close_modal)


@pytest.mark.asyncio
async def test_showcase_modal_stays_centered_and_clickable_across_resize():
    """A resize must not move the modal or its close target outside the viewport."""
    app = showcase_app()
    async with app.run_test(size=(80, 24)) as pilot:
        navigation = app.document.get_by_id("navigation")
        assert await pilot.click(navigation.items[3])
        await pilot.pause()
        opener = app.document.get_by_id("open-modal")
        opener.scroll_visible(animate=False)
        assert await pilot.click(opener)
        await pilot.pause()
        await pilot.resize_terminal(60, 20)
        await pilot.pause()
        panel = app.screen.query_one(".markup-modal-content")
        close_modal = app.document.get_by_id("close-modal")
        assert app.screen.region.contains_region(panel.region)
        assert app.screen.region.contains_region(close_modal.region)
        assert abs(panel.region.center[0] - app.screen.region.center[0]) <= 1
        assert abs(panel.region.center[1] - app.screen.region.center[1]) <= 1
        x = close_modal.region.x + close_modal.region.width // 2
        y = close_modal.region.y + close_modal.region.height // 2
        assert app.get_widget_at(x, y)[0] is close_modal
        assert await pilot.click(close_modal)
        await pilot.pause()
        await pilot.resize_terminal(80, 24)
        assert await pilot.click(opener)
        await pilot.pause()
        assert await pilot.click("#close-modal")


@pytest.mark.asyncio
async def test_long_modal_content_keeps_action_reachable_on_short_terminal():
    """Long dialog bodies must not strand their only dismissal action below the screen."""
    labels = "".join(f"<label>Line {number}: a long modal explanation.</label>" for number in range(20))
    markup = f'''<ui>
      <button id="open" on-pressed="open_modal">Open</button>
      <modal id="long">{labels}<button id="close" on-pressed="close_modal">Close</button></modal>
    </ui>'''

    def open_modal(context):
        context.push_modal("long")

    def close_modal(context):
        context.dismiss_modal("closed")

    app = TextUI(DocumentLoader().from_string(markup), actions={"open_modal": open_modal, "close_modal": close_modal})
    async with app.run_test(size=(60, 20)) as pilot:
        assert await pilot.click("#open")
        await pilot.pause()
        panel = app.screen.query_one(".markup-modal-content")
        assert app.screen.region.contains_region(panel.region)
        close = app.document.get_by_id("close")
        close.scroll_visible(animate=False)
        await pilot.pause()
        assert app.screen.region.contains_region(close.region)
        assert await pilot.click(close)


@pytest.mark.asyncio
async def test_showcase_divider_drag_survives_sidebar_toggle_and_resize():
    """Sidebar layout state must remain usable after pointer resizing and a narrow viewport."""
    app = showcase_app()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        split = app.document.get_by_id("layout")
        sidebar = app.document.get_by_id("sidebar")
        await pilot.mouse_down(split.divider)
        await pilot.hover(offset=(30, 4))
        await pilot.mouse_up(offset=(30, 4))
        await pilot.pause()
        resized_width = sidebar.region.width
        assert resized_width == 30
        toggle = app.document.get_by_id("toggle-sidebar")
        assert await pilot.click(toggle, offset=(toggle.region.width // 2, toggle.region.height // 2))
        await pilot.pause(0.25)
        assert await pilot.click(toggle, offset=(toggle.region.width // 2, toggle.region.height // 2))
        await pilot.pause(0.25)
        assert sidebar.region.width == resized_width
        await pilot.resize_terminal(60, 20)
        await pilot.pause()
        assert app.screen.region.contains_region(app.document.get_by_id("feedback").region)
