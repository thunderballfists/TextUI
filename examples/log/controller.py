from rich.text import Text

from textui import action


def _transcript():
    return window.document.get_by_id("transcript")


@action
def append_status() -> None:
    _transcript().append(Text("Connected", style="green"))
    window.document.get_by_id("feedback").update("Added a styled status entry")


@action
def stream_message() -> None:
    transcript = _transcript()
    for delta in ("Reply ", "streamed in ", "three deltas."):
        transcript.append_inline(delta)
    transcript.commit_line()
    window.document.get_by_id("feedback").update("Committed the streamed entry")
