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
async def test_list_rejects_rows_that_cannot_fill_its_label_pattern():
    app = TextUI(DocumentLoader().from_string('<ui><list id="agents" item-label="{name}" /></ui>'))
    async with app.run_test():
        agents = app.document.get_by_id("agents")
        with pytest.raises(ValueError, match="name"):
            await agents.set_items([{"id": "alpha"}])
