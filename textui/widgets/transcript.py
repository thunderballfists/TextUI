"""A RichLog adapter with efficient streamed-line updates."""
from __future__ import annotations

from rich.console import RenderableType
from rich.cells import cell_len
from rich.segment import Segment
from rich.text import Text
from textual.geometry import Size
from textual.reactive import var
from textual.strip import Strip
from textual.widgets import RichLog

from ..registry import AttributeSpec, BuildContext, ComponentRegistry, ComponentSpec, boolean, integer


class TranscriptLog(RichLog):
    """A RichLog with committed entries and one replaceable streamed entry."""

    is_following: var[bool] = var(True)

    def __init__(
        self,
        *,
        max_lines: int | None = None,
        wrap: bool = False,
        highlight: bool = False,
        markup: bool = False,
        auto_scroll: bool = True,
    ) -> None:
        super().__init__(
            max_lines=max_lines,
            wrap=wrap,
            highlight=highlight,
            markup=markup,
            auto_scroll=auto_scroll,
        )
        self.is_following = auto_scroll
        self._inline_text = ""
        self._inline_line_count = 0
        self._inline_open = False
        self._inline_pending = False
        # Width and printability of `_inline_text`, tracked incrementally so
        # extending a streamed line stays proportional to the delta rather than
        # rescanning everything accumulated so far.
        self._inline_width = 0
        self._inline_printable = True

    def watch_scroll_y(self, old_value: float, new_value: float) -> None:
        super().watch_scroll_y(old_value, new_value)
        self.is_following = self.is_vertical_scroll_end

    def append(self, content: RenderableType | object) -> TranscriptLog:
        """Write a complete, optionally Rich, transcript entry."""
        self.commit_line()
        self.write(content, scroll_end=self.auto_scroll and self.is_following)
        return self

    def append_inline(self, text: str) -> TranscriptLog:
        """Replace the active literal streamed entry with its extended text."""
        if not isinstance(text, str):
            raise TypeError("append_inline text must be a string")
        if not self._size_known:
            self._inline_text += text
            self._inline_open = True
            if not self._inline_pending:
                self._inline_pending = True
                self.call_after_refresh(self._write_pending_inline)
            return self
        if self._can_extend_inline(text):
            self._append_inline_delta(text)
            self._inline_text += text
            return self
        self._discard_inline()
        self._inline_text += text
        old_line_ids = {id(line) for line in self.lines}
        self.write(Text(self._inline_text), scroll_end=self.auto_scroll and self.is_following)
        self._inline_line_count = 0
        for line in reversed(self.lines):
            if id(line) in old_line_ids:
                break
            self._inline_line_count += 1
        self._inline_open = self._inline_line_count > 0
        # Re-derive the incremental state from the text actually written, so the
        # fast path can trust it on the next delta.
        self._inline_width = cell_len(self._inline_text)
        self._inline_printable = self._inline_text.isprintable()
        return self

    def _write_pending_inline(self) -> None:
        if not self._size_known:
            self.call_after_refresh(self._write_pending_inline)
            return
        self._inline_pending = False
        if not self._inline_open:
            return
        self.append_inline("")

    def commit_line(self) -> TranscriptLog:
        """Finalize the active streamed entry without adding another line."""
        if self._inline_pending:
            self.write(Text(self._inline_text), scroll_end=self.auto_scroll and self.is_following)
        self._inline_text = ""
        self._inline_line_count = 0
        self._inline_open = False
        self._inline_pending = False
        self._inline_width = 0
        self._inline_printable = True
        return self

    def clear(self) -> TranscriptLog:
        super().clear()
        self._inline_text = ""
        self._inline_line_count = 0
        self._inline_open = False
        self._inline_pending = False
        self._inline_width = 0
        self._inline_printable = True
        self.is_following = self.auto_scroll
        return self

    def _discard_inline(self) -> None:
        if not self._inline_open:
            return
        if self._inline_line_count:
            del self.lines[-self._inline_line_count:]
        self._line_cache.clear()
        self.virtual_size = Size(self._widest_line_width, len(self.lines))
        self.refresh()

    def _can_extend_inline(self, text: str) -> bool:
        return (
            self._inline_open
            and self._inline_line_count == 1
            and not self.wrap
            and self._inline_printable
            and text.isprintable()
        )

    def _append_inline_delta(self, text: str) -> None:
        previous_width = self._inline_width
        delta_width = cell_len(text)
        extended = self.lines[-1].crop(0, previous_width) + Strip([Segment(text)], delta_width)
        total_width = previous_width + delta_width
        line_width = max(total_width, self.min_width)
        self.lines[-1] = extended.adjust_cell_length(line_width)
        self._inline_width = total_width
        self._widest_line_width = max(self._widest_line_width, total_width)
        self._line_cache.clear()
        self.virtual_size = Size(self._widest_line_width, len(self.lines))
        self.refresh()
        if self.auto_scroll and self.is_following:
            self.scroll_end(animate=False, immediate=False, x_axis=False)


def build_log(context: BuildContext) -> TranscriptLog:
    return TranscriptLog(
        max_lines=context.attributes.get("max-lines"),
        wrap=context.attributes["wrap"],
        highlight=context.attributes["highlight"],
        markup=context.attributes["markup"],
        auto_scroll=context.attributes["auto-scroll"],
    )


def register_transcript(registry: ComponentRegistry) -> None:
    registry.register(ComponentSpec(
        tag="log", factory=build_log,
        attributes={
            "max-lines": AttributeSpec(integer(minimum=1)),
            "wrap": AttributeSpec(boolean, default=False),
            "highlight": AttributeSpec(boolean, default=False),
            "markup": AttributeSpec(boolean, default=False),
            "auto-scroll": AttributeSpec(boolean, default=True),
        },
    ))
