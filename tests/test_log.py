import pytest
from rich.cells import cell_len
from rich.text import Text
from textual.widgets import RichLog

from textui import DocumentLoader, DocumentValidationError, TextUI
from textui.widgets import transcript as transcript_module


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
@pytest.mark.parametrize(
    ("finalizer", "expected"),
    [
        ("commit", ["token"]),
        ("append", ["token", "complete"]),
    ],
)
async def test_log_keeps_inline_text_finalized_before_its_first_layout(finalizer, expected):
    class PreLayoutApp(TextUI):
        def on_mount(self) -> None:
            log = self.document.get_by_id("transcript")
            log.append_inline("token")
            if finalizer == "commit":
                log.commit_line()
            else:
                log.append("complete")

    app = PreLayoutApp(DocumentLoader().from_string('<ui><log id="transcript" /></ui>'))
    async with app.run_test(size=(40, 8)):
        log = app.document.get_by_id("transcript")
        assert [line.text.rstrip() for line in log.lines] == expected


@pytest.mark.asyncio
async def test_log_streams_a_long_single_line_with_linear_rendered_text(monkeypatch):
    rendered_character_count = 0
    rich_log_write = RichLog.write

    def track_rendered_text(self, content, *args, **kwargs):
        nonlocal rendered_character_count
        if isinstance(content, Text):
            rendered_character_count += len(content.plain)
        return rich_log_write(self, content, *args, **kwargs)

    monkeypatch.setattr(RichLog, "write", track_rendered_text)
    app = TextUI(DocumentLoader().from_string('<ui><log id="transcript" /></ui>'))
    async with app.run_test(size=(40, 8)):
        log = app.document.get_by_id("transcript")
        for _ in range(200):
            log.append_inline("x")

        assert "".join(line.text.rstrip() for line in log.lines) == "x" * 200
        assert rendered_character_count <= 400


@pytest.mark.asyncio
async def test_log_renders_control_character_deltas_through_rich():
    app = TextUI(DocumentLoader().from_string('<ui><log id="transcript" /></ui>'))
    async with app.run_test(size=(40, 8)):
        log = app.document.get_by_id("transcript")
        log.append_inline("before")
        log.append_inline("\x07after")

        assert "\x07" not in "".join(line.text for line in log.lines)


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



@pytest.mark.asyncio
async def test_log_streams_without_rescanning_accumulated_text(monkeypatch):
    """Per-delta work must be proportional to the delta, not the whole line.

    The printability check and the width measurement previously ran over
    `_inline_text + text` on every delta, making a long streamed line quadratic
    even though the rendered output was already linear.
    """
    measured_characters = 0
    real_cell_len = transcript_module.cell_len

    def counting_cell_len(text):
        nonlocal measured_characters
        measured_characters += len(text)
        return real_cell_len(text)

    monkeypatch.setattr(transcript_module, "cell_len", counting_cell_len)

    app = TextUI(DocumentLoader().from_string('<ui><log id="transcript" /></ui>'))
    async with app.run_test(size=(40, 8)):
        log = app.document.get_by_id("transcript")
        deltas = 200
        for _ in range(deltas):
            log.append_inline("x")

        assert "".join(line.text.rstrip() for line in log.lines) == "x" * deltas
        # Linear behaviour keeps this proportional to the streamed length; the
        # previous implementation measured ~deltas**2 / 2 characters.
        assert measured_characters <= deltas * 4
        # The incremental state must still agree with the text it describes.
        assert log._inline_width == real_cell_len(log._inline_text)
        assert log._inline_printable is True


@pytest.mark.asyncio
async def test_log_falls_back_when_a_delta_is_not_printable():
    """A control-character delta must still render, via the rewrite path."""
    app = TextUI(DocumentLoader().from_string('<ui><log id="transcript" /></ui>'))
    async with app.run_test(size=(40, 8)):
        log = app.document.get_by_id("transcript")
        log.append_inline("before")
        log.append_inline("\tafter")
        assert log._inline_printable is False
        assert "".join(line.text for line in log.lines).startswith("before")
        # Streaming continues to work after the fallback.
        log.append_inline("!")
        assert log._inline_width == cell_len(log._inline_text)
