import pytest

from textui import DocumentLoader, TextUI


MARKUP = '''<ui>
  <button id="open" on-pressed="open_modal">Open</button>
  <label id="result">Waiting</label>
  <modal id="pick" dismissable="true">
    <label>Choose an account</label>
    <button id="choose" on-pressed="choose">Choose Alpha</button>
  </modal>
</ui>'''


@pytest.mark.asyncio
async def test_declared_modal_returns_a_dismissal_value_and_esc_cancels():
    async def open_modal(context):
        value = await context.push_modal("pick")
        context.document.get_by_id("result").update(str(value))

    def choose(context):
        context.dismiss_modal("alpha")

    app = TextUI(DocumentLoader().from_string(MARKUP), actions={"open_modal": open_modal, "choose": choose})
    async with app.run_test() as pilot:
        await pilot.click("#open")
        await pilot.pause()
        assert app.screen.id == "pick"
        await pilot.click("#choose")
        await pilot.pause()
        assert str(app.document.get_by_id("result").render()) == "alpha"

        await pilot.click("#open")
        await pilot.press("escape")
        await pilot.pause()
        assert str(app.document.get_by_id("result").render()) == "None"
