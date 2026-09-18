"""Exercise the runnable examples through their real document bindings."""

import pytest


@pytest.mark.asyncio
async def test_editor_save_updates_status_from_any_working_directory(tmp_path, monkeypatch):
    from examples.editor import Editor

    monkeypatch.chdir(tmp_path)
    app = Editor()
    async with app.run_test() as pilot:
        name = app.document.get_by_id("name")
        status = app.document.get_by_id("status")
        assert str(status.render()) == "Ready"
        name.value = "notes [draft]"
        assert await pilot.click("#save")
        assert str(status.render()) == "Saved notes [draft]"
        assert status.visible
