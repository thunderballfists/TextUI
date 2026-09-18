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


@pytest.mark.asyncio
async def test_sample_markup_mounts_all_builtin_widgets(tmp_path, monkeypatch):
    from pathlib import Path

    import textui

    monkeypatch.chdir(tmp_path)
    source = Path(__file__).parents[1] / "examples" / "sample_markup.xml"
    document = textui.DocumentLoader().from_file(source)
    app = textui.TextUI(document)
    async with app.run_test():
        assert app.document.get_by_id("sample").id == "sample"
        assert app.document.get_by_id("name").id == "name"
        assert app.document.get_by_id("notify").value is False
        assert app.document.get_by_id("sample-button").label.plain == "A native button"
