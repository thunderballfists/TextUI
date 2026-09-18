import pytest
from rich.text import Text

from textui import DocumentLoader, DocumentValidationError, TextUI


MARKUP = '''<ui>
  <log id="transcript" max-lines="20" wrap="true" highlight="true" markup="false" auto-scroll="true" />
</ui>'''


def test_log_lowers_typed_native_attributes():
    document = DocumentLoader().from_string(MARKUP)
    log = document.nodes[0]
    assert log.attributes == {
        "max-lines": 20,
        "wrap": True,
        "highlight": True,
        "markup": False,
        "auto-scroll": True,
    }


@pytest.mark.parametrize("markup", [
    '<ui><log max-lines="0" /></ui>',
    '<ui><log wrap="sometimes" /></ui>',
    '<ui><log>Initial text is not supported</log></ui>',
])
def test_log_rejects_invalid_attributes_and_content(markup):
    with pytest.raises(DocumentValidationError):
        DocumentLoader().from_string(markup)


@pytest.mark.asyncio
async def test_log_commits_rich_lines_and_grows_one_literal_stream_line():
    app = TextUI(DocumentLoader().from_string(MARKUP))
    async with app.run_test(size=(40, 8)):
        log = app.document.get_by_id("transcript")
        log.append(Text("ready", style="green"))
        log.append_inline("[red]The ")
        log.append_inline("forecast[/red]")
        log.commit_line()
        log.append("complete")

        assert [line.text.rstrip() for line in log.lines] == [
            "ready",
            "[red]The forecast[/red]",
            "complete",
        ]


@pytest.mark.asyncio
async def test_log_replaces_the_active_stream_line_when_retention_trims_history():
    app = TextUI(DocumentLoader().from_string('<ui><log id="transcript" max-lines="3" /></ui>'))
    async with app.run_test(size=(40, 8)):
        log = app.document.get_by_id("transcript")
        log.append("one")
        log.append("two")
        log.append("three")
        log.append_inline("four")
        log.append_inline(" extended")

        assert [line.text.rstrip() for line in log.lines] == [
            "two",
            "three",
            "four extended",
        ]


@pytest.mark.asyncio
async def test_log_pauses_following_after_user_scrolls_away_from_tail():
    app = TextUI(DocumentLoader().from_string('<ui><log id="transcript" /></ui>'))
    async with app.run_test(size=(40, 4)) as pilot:
        log = app.document.get_by_id("transcript")
        for number in range(8):
            log.append(f"line {number}")
        await pilot.pause()
        assert log.is_following is True
        log.scroll_home(immediate=True, animate=False)
        await pilot.pause()
        assert log.is_following is False
        log.append("new line")
        assert log.is_vertical_scroll_end is False
        log.scroll_end(immediate=True, animate=False)
        await pilot.pause()
        assert log.is_following is True
