import pytest

from textui import DocumentLoader, DocumentStateError, TextUI


MODAL_MARKUP = '''<ui>
  <button id="open" on-pressed="open_modal">Open</button>
  <label id="result">Waiting</label>
  <modal id="pick" dismissable="true">
    <label>Choose an account</label>
    <button id="choose" on-pressed="choose">Choose Alpha</button>
  </modal>
</ui>'''


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [(120, 50), (80, 24)])
async def test_modal_reopens_with_visible_click_target_and_restores_focus(size):
    """A hidden or stale rebuilt modal must fail through its real button hit target."""
    results = []

    async def open_modal(context):
        results.append(await context.push_modal("pick"))

    def choose(context):
        context.dismiss_modal("alpha")

    app = TextUI(
        DocumentLoader().from_string(MODAL_MARKUP),
        actions={"open_modal": open_modal, "choose": choose},
    )
    async with app.run_test(size=size) as pilot:
        base_screen = app.screen
        screens = []
        choices = []
        for expected in ("alpha", None, "alpha"):
            opener = app.document.get_by_id("open")
            opener.focus()
            assert await pilot.click(opener)
            await pilot.pause()
            screen = app.screen
            choose_button = app.document.get_by_id("choose")
            panel = screen.query_one(".markup-modal-content")
            assert panel.region.width >= 28
            assert screen.region.contains_region(panel.region)
            assert choose_button.region.width > 0
            assert choose_button.region.height > 0
            assert screen.region.contains_region(choose_button.region)
            x = choose_button.region.x + choose_button.region.width // 2
            y = choose_button.region.y + choose_button.region.height // 2
            assert app.get_widget_at(x, y)[0] is choose_button
            if expected is None:
                await pilot.press("escape")
            else:
                assert await pilot.click(choose_button, offset=(choose_button.region.width // 2, 1))
            await pilot.pause()
            assert app.screen is base_screen
            assert app.focused is opener
            assert results[-1] == expected
            with pytest.raises(DocumentStateError):
                app.document.get_by_id("choose")
            screens.append(screen)
            choices.append(choose_button)
        assert results == ["alpha", None, "alpha"]
        assert len({id(screen) for screen in screens}) == 3
        assert len({id(button) for button in choices}) == 3


@pytest.mark.asyncio
async def test_nondismissable_modal_ignores_escape_and_reopens_after_click():
    """Escape must not discard a non-dismissable modal or prevent its next open."""
    markup = MODAL_MARKUP.replace('dismissable="true"', 'dismissable="false"')
    results = []

    async def open_modal(context):
        results.append(await context.push_modal("pick"))

    def choose(context):
        context.dismiss_modal("alpha")

    app = TextUI(DocumentLoader().from_string(markup), actions={"open_modal": open_modal, "choose": choose})
    async with app.run_test() as pilot:
        for _ in range(2):
            assert await pilot.click("#open")
            await pilot.pause()
            modal = app.screen
            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is modal
            assert await pilot.click("#choose")
            await pilot.pause()
        assert results == ["alpha", "alpha"]
