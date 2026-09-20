import asyncio
from collections.abc import Mapping

import pytest

from textui import DocumentLoader, DocumentValidationError, TextUI


MARKUP = '''<ui>
  <list id="agents" item-label="{name}" on-selected="select_agent" />
</ui>'''


def test_list_requires_a_nonempty_item_label_pattern():
    with pytest.raises(DocumentValidationError):
        DocumentLoader().from_string('<ui><list id="agents" /></ui>')
    with pytest.raises(DocumentValidationError):
        DocumentLoader().from_string('<ui><list id="agents" item-label="" /></ui>')
    with pytest.raises(DocumentValidationError, match="item-label field"):
        DocumentLoader().from_string('<ui><list id="agents" item-label="{agent.name}" /></ui>')


@pytest.mark.parametrize("pattern", ["{name}", "{count:03d}", "{{literal}}"])
def test_list_accepts_direct_item_label_fields(pattern: str):
    DocumentLoader().from_string(f'<ui><list id="agents" item-label="{pattern}" /></ui>')


@pytest.mark.parametrize("pattern", ["{name:{width.foo}}", "{name:{width[0]}}", "{name:{width}"])
def test_list_rejects_nested_non_mapping_item_label_fields(pattern: str):
    with pytest.raises(DocumentValidationError, match="item-label"):
        DocumentLoader().from_string(f'<ui><list id="agents" item-label="{pattern}" /></ui>')


@pytest.mark.asyncio
async def test_list_sets_mapping_rows_and_reports_the_selected_item():
    seen: list[tuple[Mapping[str, object], int]] = []

    def select_agent(context) -> None:
        seen.append((context.event.item, context.event.index))

    app = TextUI(DocumentLoader().from_string(MARKUP), actions={"select_agent": select_agent})
    async with app.run_test(size=(40, 8)) as pilot:
        agents = app.document.get_by_id("agents")
        await agents.set_items([
            {"id": "alpha", "name": "Alpha"},
            {"id": "bravo", "name": "Bravo"},
        ])
        await pilot.pause()
        await pilot.pause()

        assert [item.item["name"] for item in agents.items] == ["Alpha", "Bravo"]
        assert agents.selected is None
        await pilot.click(agents.items[1], offset=(1, 0))
        await pilot.pause()
        assert agents.selected == {"id": "bravo", "name": "Bravo"}
        assert seen == [({"id": "bravo", "name": "Bravo"}, 1)]


@pytest.mark.asyncio
async def test_list_keyboard_selection_and_replacement_keep_data_in_sync():
    app = TextUI(DocumentLoader().from_string('<ui><list id="agents" item-label="{name}" /></ui>'))
    async with app.run_test(size=(40, 8)) as pilot:
        agents = app.document.get_by_id("agents")
        await agents.set_items([{"name": "Alpha"}, {"name": "Bravo"}])
        agents.focus()
        await pilot.press("down", "enter")
        await pilot.pause()
        assert agents.selected == {"name": "Bravo"}

        await agents.set_items([{"name": "Charlie"}])
        assert [item.item["name"] for item in agents.items] == ["Charlie"]
        assert agents.selected is None


@pytest.mark.asyncio
async def test_list_serializes_overlapping_replacements(monkeypatch):
    app = TextUI(DocumentLoader().from_string('<ui><list id="agents" item-label="{name}" /></ui>'))
    async with app.run_test() as pilot:
        agents = app.document.get_by_id("agents")
        remove_children = agents.remove_children
        first_removal_started = asyncio.Event()
        release_first_removal = asyncio.Event()
        removals = 0

        async def pause_first_removal():
            nonlocal removals
            removals += 1
            if removals == 1:
                first_removal_started.set()
                await release_first_removal.wait()
            await remove_children()

        monkeypatch.setattr(agents, "remove_children", pause_first_removal)
        first = asyncio.create_task(agents.set_items([{"name": "Alpha"}]))
        await first_removal_started.wait()
        latest = asyncio.create_task(agents.set_items([{"name": "Bravo"}]))
        await asyncio.sleep(0)
        release_first_removal.set()
        await asyncio.gather(first, latest)
        await pilot.pause()

        assert [item.item["name"] for item in agents.items] == ["Bravo"]
        assert tuple(agents.children) == agents.items
        assert agents.index == 0


@pytest.mark.asyncio
async def test_list_rejects_rows_that_cannot_fill_its_label_pattern():
    app = TextUI(DocumentLoader().from_string('<ui><list id="agents" item-label="{name}" /></ui>'))
    async with app.run_test():
        agents = app.document.get_by_id("agents")
        with pytest.raises(ValueError, match="name"):
            await agents.set_items([{"id": "alpha"}])
