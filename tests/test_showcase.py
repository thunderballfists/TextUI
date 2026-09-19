"""Exercise the all-features showcase through the project runtime."""

from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_showcase_mounts_components_runtime_data_and_modal():
    from textui import ProjectApp, ProjectSource

    entry = Path(__file__).parents[1] / "examples" / "showcase" / "app.ui"
    app = ProjectApp(ProjectSource.discover(entry))
    async with app.run_test(size=(120, 50)) as pilot:
        assert app.document.get_by_id("showcase").id == "showcase"
        assert app.document.get_by_id("agents").id == "agents"
        assert app.document.get_by_id("jobs").get_cell("backup", "state").plain == "Running"
        await pilot.click(app.document.get_by_id("navigation").items[2])
        await pilot.pause()
        app.document.get_by_id("add-data").press()
        await pilot.pause()
        assert app.document.get_by_id("jobs").get_cell("deploy", "state") == "Queued"
        await pilot.click(app.document.get_by_id("navigation").items[3])
        await pilot.pause()
        app.document.get_by_id("open-modal").press()
        await pilot.pause()
        assert app.screen.id == "help"
        app.document.get_by_id("close-modal").press()
        await pilot.pause()
