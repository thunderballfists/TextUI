"""Exercise the all-features showcase through the project runtime."""

from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_showcase_mounts_components_runtime_data_and_modal():
    from textui import ProjectApp, ProjectSource
    from textual.widgets import Button, DataTable

    entry = Path(__file__).parents[1] / "examples" / "showcase" / "app.ui"
    app = ProjectApp(ProjectSource.discover(entry))
    async with app.run_test(size=(120, 50)) as pilot:
        assert app.document.get_by_id("showcase").id == "showcase"
        header = app.document.get_by_id("top-bar")
        help_button = app.document.get_by_id("open-modal")
        assert help_button.region.x + help_button.region.width == header.region.x + header.region.width
        assert app.document.get_by_id("quit").variant == "error"
        assert app.document.get_by_id("quit").styles.padding.top == 0
        assert app.document.get_by_id("agents").id == "agents"
        assert app.document.get_by_id("jobs").get_cell("backup", "state").plain == "Running"
        await pilot.pause(1.05)
        assert str(app.document.get_by_id("clock").render()) != "Starting…"
        app.document.get_by_id("alpha").query_one(Button).press()
        await pilot.pause()
        assert str(app.document.get_by_id("feedback").render()) == "Alpha selected from a component slot"
        app.document.get_by_id("toggle-sidebar").press()
        await pilot.pause()
        assert app.document.get_by_id("sidebar").display is False
        app.document.get_by_id("toggle-sidebar").press()
        await pilot.click(app.document.get_by_id("navigation").items[1])
        await pilot.pause()
        volume = app.document.get_by_id("volume")
        assert volume.value == 40
        volume.focus()
        await pilot.press("right")
        await pilot.pause()
        assert str(app.document.get_by_id("feedback").render()) == "Volume: 45"
        await pilot.press("2")
        await pilot.pause()
        assert app.document.get_by_id("tabs").active == "details"
        await pilot.click(app.document.get_by_id("navigation").items[2])
        await pilot.pause()
        usage = app.document.get_by_id("usage")
        assert len(usage.rows) == 0
        app.document.get_by_id("refresh-usage").press()
        await pilot.pause()
        assert usage.get_cell("2026-09-19-alpha", "requests").plain == "42"
        assert usage.zebra_stripes is True
        assert usage.column_borders is True
        assert usage.resizable is True
        usage.focus()
        await pilot.press("ctrl+right")
        await pilot.pause()
        assert usage.columns["date"].auto_width is False
        usage.focus()
        await pilot.press("enter")
        await pilot.pause()
        assert str(app.document.get_by_id("feedback").render()) == "Usage: 42 requests"
        requests = usage.columns["requests"]
        usage.post_message(DataTable.HeaderSelected(usage, requests.key, 1, requests.label))
        await pilot.pause()
        assert [key.value for key in usage.rows] == [
            "2026-09-19-bravo",
            "2026-09-19-alpha",
        ]
        app.document.get_by_id("add-data").press()
        await pilot.pause()
        assert app.document.get_by_id("jobs").get_cell("deploy", "state") == "Queued"
        app.document.get_by_id("files").select_node(app.document.get_by_id("files").root.children[0])
        await pilot.pause()
        assert str(app.document.get_by_id("feedback").render()) == "File: src"
        await pilot.click(app.document.get_by_id("navigation").items[3])
        await pilot.pause()
        app.document.get_by_id("agents").action_select_cursor()
        await pilot.pause()
        assert str(app.document.get_by_id("agent-detail").render()) == "Alpha: Ready"
        app.document.get_by_id("append-log").press()
        await pilot.pause()
        assert str(app.document.get_by_id("feedback").render()) == "Log appended"
        assert await pilot.click("#open-modal")
        await pilot.pause()
        assert app.screen.id == "help"
        first_modal = app.screen
        assert await pilot.click("#close-modal")
        await pilot.pause()
        assert await pilot.click("#open-modal")
        await pilot.pause()
        assert app.screen.id == "help"
        assert app.screen is not first_modal
        assert await pilot.click("#close-modal")
        await pilot.pause()
        assert app.screen is not first_modal
        assert app.screen.id != "help"


@pytest.mark.asyncio
async def test_showcase_quit_control_uses_a_shared_command():
    from textui import ProjectApp, ProjectSource

    entry = Path(__file__).parents[1] / "examples" / "showcase" / "app.ui"
    app = ProjectApp(ProjectSource.discover(entry))

    async with app.run_test():
        quit_button = app.document.get_by_id("quit")
        assert quit_button._textui_command_name == "quit_app"
        assert quit_button.label.plain == "Quit"
        assert app.controllers.commands["quit_app"].shortcut == "ctrl+q"


@pytest.mark.asyncio
async def test_showcase_toggles_its_declared_compact_preset():
    from textui import ProjectApp, ProjectSource

    entry = Path(__file__).parents[1] / "examples" / "showcase" / "app.ui"
    app = ProjectApp(ProjectSource.discover(entry))

    async with app.run_test() as pilot:
        quit_button = app.document.get_by_id("quit")
        toggle = app.document.get_by_id("toggle-compact")
        layout = app.document.get_by_id("layout")
        assert quit_button.styles.padding.left == 1
        assert layout.region.y < app.size.height
        toggle.press()
        await pilot.pause()
        assert quit_button.styles.padding.left == 0
        assert layout.region.y < app.size.height
        assert str(app.document.get_by_id("feedback").render()) == "Compact controls off"


@pytest.mark.asyncio
async def test_showcase_toggles_its_declared_button_border_preset():
    from textui import ProjectApp, ProjectSource

    entry = Path(__file__).parents[1] / "examples" / "showcase" / "app.ui"
    app = ProjectApp(ProjectSource.discover(entry))

    async with app.run_test() as pilot:
        toggle = app.document.get_by_id("toggle-borders")
        assert toggle._textui_command_name == "toggle_borders"
        toggle.press()
        await pilot.pause()
        assert str(app.document.get_by_id("feedback").render()) == "Button borders off"
